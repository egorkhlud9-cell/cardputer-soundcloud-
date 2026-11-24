/*
 * SPDX-License-Identifier: MIT
 * CloudZero - animated SoundCloud companion for Cardputer Zero.
 */
#include "app.h"
#include "linux_input.h"
#include "lvgl.h"
#if !USE_DESKTOP
#include "src/drivers/display/fb/lv_linux_fbdev.h"
#endif
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#ifndef APP_FRAMEBUFFER_DEVICE
#define APP_FRAMEBUFFER_DEVICE "/dev/fb0"
#endif

namespace app {
namespace {
lv_obj_t *screen=nullptr,*title_label=nullptr,*artist_label=nullptr,*status_label=nullptr;
lv_obj_t *progress_bar=nullptr,*time_label=nullptr,*cover=nullptr,*cover_mark=nullptr;
lv_obj_t *page_label=nullptr,*detail_label=nullptr,*eq[3]={nullptr,nullptr,nullptr};
lv_obj_t *play_button_label=nullptr;
bool playing=false,connected=false;
int queue_count=0,page=0,sleep_minutes=0,sleep_remaining=0;
uint32_t last_poll=0,last_second=0;
std::string last_title;

std::string http_request(const char* method,const char* path,const std::string& body="") {
    int fd=::socket(AF_INET,SOCK_STREAM,0); if(fd<0)return {};
    timeval tv{0,180000};
    setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));
    setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&tv,sizeof(tv));
    sockaddr_in addr{};addr.sin_family=AF_INET;addr.sin_port=htons(8765);
    inet_pton(AF_INET,"127.0.0.1",&addr.sin_addr);
    if(::connect(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))<0){::close(fd);return {};}
    char head[512];
    int n=std::snprintf(head,sizeof(head),
      "%s %s HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\nContent-Type: application/json\r\nContent-Length: %zu\r\n\r\n",
      method,path,body.size());
    ::send(fd,head,n,0);if(!body.empty())::send(fd,body.data(),body.size(),0);
    std::string response;char buf[1024];
    while((n=::recv(fd,buf,sizeof(buf),0))>0)response.append(buf,n);
    ::close(fd);auto split=response.find("\r\n\r\n");
    return split==std::string::npos?std::string():response.substr(split+4);
}
std::string json_string(const std::string& j,const char* key,const char* fallback="") {
    std::string needle=std::string("\"")+key+"\"";auto p=j.find(needle);
    if(p==std::string::npos)return fallback;p=j.find(':',p+needle.size());
    if(p==std::string::npos)return fallback;p=j.find('"',p+1);
    if(p==std::string::npos)return fallback;
    std::string out;bool esc=false;
    for(++p;p<j.size();++p){char c=j[p];if(esc){out+=c=='n'?' ':c;esc=false;}
      else if(c=='\\')esc=true;else if(c=='"')break;else out+=c;}
    return out.empty()?fallback:out;
}
double json_number(const std::string& j,const char* key) {
    std::string needle=std::string("\"")+key+"\"";auto p=j.find(needle);
    if(p==std::string::npos)return 0;p=j.find(':',p+needle.size());
    return p==std::string::npos?0:std::atof(j.c_str()+p+1);
}
bool json_bool(const std::string& j,const char* key) {
    std::string needle=std::string("\"")+key+"\"";auto p=j.find(needle);
    if(p==std::string::npos)return false;p=j.find(':',p+needle.size());
    if(p==std::string::npos)return false;
    p=j.find_first_not_of(" \t\r\n",p+1);
    return p!=std::string::npos && j.compare(p,4,"true")==0;
}
void set_text(lv_obj_t* o,const std::string& s){if(o)lv_label_set_text(o,s.c_str());}
void command(const char* c){http_request("POST","/api/command",std::string("{\"command\":\"")+c+"\"}");}
void fade_in(lv_obj_t* obj){
    if(!obj)return;lv_anim_t a;lv_anim_init(&a);lv_anim_set_var(&a,obj);
    lv_anim_set_values(&a,80,255);lv_anim_set_duration(&a,220);
    lv_anim_set_exec_cb(&a,[](void* v,int32_t n){lv_obj_set_style_opa(static_cast<lv_obj_t*>(v),static_cast<lv_opa_t>(n),0);});
    lv_anim_start(&a);
}
void equalizer_anim(void* target,int32_t h){
    auto* bar=static_cast<lv_obj_t*>(target);if(!bar||!lv_obj_is_valid(bar))return;
    lv_obj_set_height(bar,h);lv_obj_align(bar,LV_ALIGN_TOP_RIGHT,-(8+(int)(intptr_t)lv_obj_get_user_data(bar)*6),8+(14-h));
}
void animate_equalizer(bool enabled){
    for(int i=0;i<3;i++){
      if(!eq[i])continue;
      lv_anim_delete(eq[i],nullptr);
      if(enabled){
        lv_anim_t a;lv_anim_init(&a);lv_anim_set_var(&a,eq[i]);
        lv_anim_set_values(&a,4,15+i*2);lv_anim_set_duration(&a,260+i*90);
        lv_anim_set_playback_duration(&a,260+i*90);lv_anim_set_repeat_count(&a,LV_ANIM_REPEAT_INFINITE);
        lv_anim_set_exec_cb(&a,equalizer_anim);lv_anim_set_start_delay(&a,i*100);lv_anim_start(&a);
      }else{lv_obj_set_height(eq[i],4);lv_obj_align(eq[i],LV_ALIGN_TOP_RIGHT,-(8+i*6),18);}
    }
}
void transport_event(lv_event_t* e){
    int id=(int)(intptr_t)lv_event_get_user_data(e);
    if(id==0)command("previous");
    else if(id==1)command("toggle");
    else if(id==2)command("next");
    else if(id==3){page=(page+1)%3;}
    else if(id==4){sleep_minutes=sleep_minutes==0?15:sleep_minutes==15?30:sleep_minutes==30?60:0;sleep_remaining=sleep_minutes*60;last_second=lv_tick_get();}
}
lv_obj_t* button(lv_obj_t* p,const char* txt,int id,int w,size_t key_index){
    auto* b=lv_button_create(p);lv_obj_set_size(b,w,25);
    lv_obj_set_style_radius(b,6,0);lv_obj_set_style_bg_color(b,lv_color_hex(id==1?0xFF5500:0x202020),0);
    lv_obj_set_style_border_color(b,lv_color_hex(0xFF6A22),0);lv_obj_set_style_border_width(b,1,0);
    lv_obj_add_event_cb(b,transport_event,LV_EVENT_CLICKED,(void*)(intptr_t)id);
    platform::register_nav_button(key_index,b);
    auto* l=lv_label_create(b);lv_label_set_text(l,txt);
    lv_obj_set_style_text_color(l,lv_color_hex(id==1?0x080808:0xF5F5F5),0);lv_obj_center(l);
    if(id==1)play_button_label=l;
    return b;
}
void poll_state(){
    auto j=http_request("GET","/api/state");
    if(j.empty()){connected=false;set_text(status_label,"PHONE LINK OFFLINE");animate_equalizer(false);return;}
    connected=true;
    std::string title=json_string(j,"title","Nothing playing");
    std::string artist=json_string(j,"artist","Open CloudZero on your phone");
    playing=json_bool(j,"playing");queue_count=(int)json_number(j,"queue_count");
    double pos=json_number(j,"position"),dur=json_number(j,"duration");
    if(title!=last_title){last_title=title;set_text(title_label,title);fade_in(title_label);}
    set_text(artist_label,artist);
    set_text(status_label,playing?"●  STREAM LINKED":"Ⅱ  PAUSED");
    if(play_button_label)lv_label_set_text(play_button_label,playing?"PAUSE":"PLAY");
    animate_equalizer(playing);
    if(progress_bar)lv_bar_set_value(progress_bar,dur>0?(int)std::clamp(pos/dur*1000.0,0.0,1000.0):0,LV_ANIM_ON);
    char t[32];std::snprintf(t,sizeof(t),"%02d:%02d  /  %02d:%02d",(int)pos/60000,((int)pos/1000)%60,(int)dur/60000,((int)dur/1000)%60);
    set_text(time_label,t);
}
void render_page(){
    if(!screen)return;
    if(page==0){
      set_text(page_label,"NOW PLAYING");
      lv_obj_clear_flag(cover,LV_OBJ_FLAG_HIDDEN);lv_obj_clear_flag(progress_bar,LV_OBJ_FLAG_HIDDEN);
      lv_obj_clear_flag(time_label,LV_OBJ_FLAG_HIDDEN);lv_obj_clear_flag(artist_label,LV_OBJ_FLAG_HIDDEN);
      set_text(detail_label,"SOUNDCLOUD  /  PHONE LINK");
      set_text(status_label,connected?(playing?"●  PLAYING":"Ⅱ  PAUSED"):"PHONE LINK OFFLINE");
    }else if(page==1){
      set_text(page_label,"UP NEXT");
      lv_obj_add_flag(cover,LV_OBJ_FLAG_HIDDEN);lv_obj_add_flag(progress_bar,LV_OBJ_FLAG_HIDDEN);
      lv_obj_add_flag(time_label,LV_OBJ_FLAG_HIDDEN);
      set_text(title_label,queue_count?std::to_string(queue_count)+" TRACKS IN QUEUE":"YOUR QUEUE IS EMPTY");
      set_text(artist_label,"Edit the queue from the phone remote");
      set_text(detail_label,"NEXT TRACKS  /  SOUNDCloud");
      set_text(status_label,"5 = PLAY/PAUSE   7 = NEXT VIEW");
    }else{
      set_text(page_label,"SLEEP MODE");
      lv_obj_add_flag(cover,LV_OBJ_FLAG_HIDDEN);lv_obj_add_flag(progress_bar,LV_OBJ_FLAG_HIDDEN);
      lv_obj_add_flag(time_label,LV_OBJ_FLAG_HIDDEN);
      set_text(title_label,"TIME TO WIND DOWN");
      set_text(artist_label,"Playback pauses when the timer ends");
      set_text(detail_label,sleep_minutes?("SLEEP TIMER  /  "+std::to_string(sleep_remaining/60)+" MIN LEFT").c_str():"SLEEP TIMER  /  OFF");
      set_text(status_label,"8 = CYCLE TIMER  /  OFF · 15 · 30 · 60");
    }
    fade_in(title_label);fade_in(detail_label);
}
}
int Application::run(){
    lv_init();
#if USE_DESKTOP
    return 2;
#else
    auto* display=lv_linux_fbdev_create();
    if(!display||lv_linux_fbdev_set_file(display,APP_FRAMEBUFFER_DEVICE)!=LV_RESULT_OK)return 1;
    platform::init_key_input(display);
    screen=lv_obj_create(nullptr);lv_obj_remove_style_all(screen);
    lv_obj_set_style_bg_color(screen,lv_color_hex(0x080808),0);lv_obj_set_style_bg_opa(screen,LV_OPA_COVER,0);
    lv_obj_clear_flag(screen,LV_OBJ_FLAG_SCROLLABLE);
    auto* brand=lv_label_create(screen);lv_label_set_text(brand,"CLOUDZERO");
    lv_obj_set_style_text_color(brand,lv_color_hex(0xFF5500),0);lv_obj_set_style_text_font(brand,&lv_font_montserrat_12,0);
    lv_obj_align(brand,LV_ALIGN_TOP_LEFT,8,5);
    page_label=lv_label_create(screen);lv_obj_set_style_text_color(page_label,lv_color_hex(0xB7B7B7),0);
    lv_obj_set_style_text_font(page_label,&lv_font_montserrat_10,0);lv_obj_align(page_label,LV_ALIGN_TOP_RIGHT,-8,7);
    for(int i=0;i<3;i++){
      eq[i]=lv_obj_create(screen);lv_obj_remove_style_all(eq[i]);lv_obj_set_size(eq[i],3,4);
      lv_obj_set_style_radius(eq[i],2,0);lv_obj_set_style_bg_color(eq[i],lv_color_hex(0xFF5500),0);
      lv_obj_set_style_bg_opa(eq[i],LV_OPA_COVER,0);lv_obj_set_user_data(eq[i],(void*)(intptr_t)i);
      lv_obj_align(eq[i],LV_ALIGN_TOP_RIGHT,-(8+i*6),18);
    }
    auto* line=lv_obj_create(screen);lv_obj_remove_style_all(line);lv_obj_set_size(line,304,1);
    lv_obj_set_style_bg_color(line,lv_color_hex(0x333333),0);lv_obj_set_style_bg_opa(line,LV_OPA_COVER,0);lv_obj_align(line,LV_ALIGN_TOP_MID,0,23);
    cover=lv_obj_create(screen);lv_obj_set_size(cover,72,72);lv_obj_set_style_radius(cover,9,0);
    lv_obj_set_style_bg_color(cover,lv_color_hex(0x1D100B),0);lv_obj_set_style_border_color(cover,lv_color_hex(0xFF5500),0);
    lv_obj_set_style_border_width(cover,2,0);lv_obj_align(cover,LV_ALIGN_TOP_RIGHT,-8,34);
    cover_mark=lv_label_create(cover);lv_label_set_text(cover_mark,"CZ");lv_obj_set_style_text_color(cover_mark,lv_color_hex(0xFF5500),0);
    lv_obj_set_style_text_font(cover_mark,&lv_font_montserrat_24,0);lv_obj_center(cover_mark);
    title_label=lv_label_create(screen);lv_obj_set_width(title_label,210);lv_label_set_long_mode(title_label,LV_LABEL_LONG_DOT);
    lv_obj_set_style_text_color(title_label,lv_color_hex(0xF5F5F5),0);lv_obj_set_style_text_font(title_label,&lv_font_montserrat_16,0);
    lv_obj_align(title_label,LV_ALIGN_TOP_LEFT,8,37);
    artist_label=lv_label_create(screen);lv_obj_set_width(artist_label,210);lv_label_set_long_mode(artist_label,LV_LABEL_LONG_DOT);
    lv_obj_set_style_text_color(artist_label,lv_color_hex(0x999999),0);lv_obj_set_style_text_font(artist_label,&lv_font_montserrat_12,0);
    lv_obj_align(artist_label,LV_ALIGN_TOP_LEFT,8,60);
    progress_bar=lv_bar_create(screen);lv_obj_set_size(progress_bar,210,5);lv_bar_set_range(progress_bar,0,1000);
    lv_obj_set_style_bg_color(progress_bar,lv_color_hex(0x303030),LV_PART_MAIN);
    lv_obj_set_style_bg_color(progress_bar,lv_color_hex(0xFF5500),LV_PART_INDICATOR);lv_obj_align(progress_bar,LV_ALIGN_TOP_LEFT,8,84);
    time_label=lv_label_create(screen);lv_obj_set_style_text_color(time_label,lv_color_hex(0x777777),0);
    lv_obj_set_style_text_font(time_label,&lv_font_montserrat_10,0);lv_obj_align(time_label,LV_ALIGN_TOP_LEFT,8,92);
    detail_label=lv_label_create(screen);lv_obj_set_style_text_color(detail_label,lv_color_hex(0xFF8844),0);
    lv_obj_set_style_text_font(detail_label,&lv_font_montserrat_10,0);lv_obj_align(detail_label,LV_ALIGN_TOP_LEFT,8,106);
    auto* controls=lv_obj_create(screen);lv_obj_remove_style_all(controls);lv_obj_set_size(controls,210,27);
    lv_obj_align(controls,LV_ALIGN_TOP_LEFT,8,126);lv_obj_set_flex_flow(controls,LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(controls,LV_FLEX_ALIGN_SPACE_BETWEEN,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);
    button(controls,"|<",0,42,0);button(controls,"PLAY",1,72,1);button(controls,">|",2,42,2);
    auto* nav=lv_obj_create(screen);lv_obj_remove_style_all(nav);lv_obj_set_size(nav,82,27);lv_obj_align(nav,LV_ALIGN_TOP_RIGHT,-5,126);
    button(nav,"VIEW",3,76,3);
    status_label=lv_label_create(screen);lv_label_set_text(status_label,"STARTING CLOUDZERO...");
    lv_obj_set_style_text_color(status_label,lv_color_hex(0x777777),0);lv_obj_set_style_text_font(status_label,&lv_font_montserrat_10,0);
    lv_obj_align(status_label,LV_ALIGN_BOTTOM_LEFT,8,-3);
    // Fifth hardware key cycles the sleep timer; the on-screen timer is on page 3.
    auto* timer_btn=lv_button_create(screen);lv_obj_set_size(timer_btn,1,1);lv_obj_add_flag(timer_btn,LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_event_cb(timer_btn,transport_event,LV_EVENT_CLICKED,(void*)(intptr_t)4);platform::register_nav_button(4,timer_btn);
    lv_screen_load(screen);render_page();
    while(true){
      lv_timer_handler();uint32_t now=lv_tick_get();
      if(now-last_poll>950){last_poll=now;poll_state();render_page();}
      if(sleep_minutes&&now-last_second>=1000){
        last_second=now;if(sleep_remaining>0)--sleep_remaining;
        if(sleep_remaining<=0){sleep_remaining=0;sleep_minutes=0;command("pause");render_page();}
        else if(page==2)render_page();
      }
      lv_delay_ms(5);
    }
    return 0;
#endif
}
}
