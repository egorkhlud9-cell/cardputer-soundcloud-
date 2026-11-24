/*
 * SPDX-License-Identifier: MIT
 * CloudZero - SoundCloud companion UI for CardputerZero.
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
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#ifndef APP_FRAMEBUFFER_DEVICE
#define APP_FRAMEBUFFER_DEVICE "/dev/fb0"
#endif

namespace app {
namespace {
lv_obj_t *title_label=nullptr, *artist_label=nullptr, *status_label=nullptr;
lv_obj_t *progress_bar=nullptr, *time_label=nullptr, *cover_mark=nullptr;
lv_obj_t *page_label=nullptr, *sleep_label=nullptr;
bool playing=false, connected=false;\nint queue_count=0;
int page=0, sleep_minutes=0, sleep_remaining=0;
uint64_t last_poll=0;

std::string http_request(const char* method, const char* path, const std::string& body="") {
    int fd=::socket(AF_INET, SOCK_STREAM, 0);
    if(fd<0) return {};
    timeval tv{0,180000};
    setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));
    setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&tv,sizeof(tv));
    sockaddr_in addr{}; addr.sin_family=AF_INET; addr.sin_port=htons(8765);
    inet_pton(AF_INET,"127.0.0.1",&addr.sin_addr);
    if(::connect(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))<0){::close(fd);return {};}
    char head[512];
    int n=std::snprintf(head,sizeof(head),
        "%s %s HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\nContent-Type: application/json\r\nContent-Length: %zu\r\n\r\n",
        method,path,body.size());
    ::send(fd,head,n,0);
    if(!body.empty()) ::send(fd,body.data(),body.size(),0);
    std::string response; char buf[1024];
    while((n=::recv(fd,buf,sizeof(buf),0))>0) response.append(buf,n);
    ::close(fd);
    auto split=response.find("\r\n\r\n");
    return split==std::string::npos?std::string():response.substr(split+4);
}
std::string json_string(const std::string& j,const char* key,const char* fallback="") {
    std::string needle=std::string("\"")+key+"\"";
    auto p=j.find(needle); if(p==std::string::npos) return fallback;
    p=j.find(':',p+needle.size()); if(p==std::string::npos) return fallback;
    p=j.find('"',p+1); if(p==std::string::npos) return fallback;
    std::string out; bool esc=false;
    for(++p;p<j.size();++p){char c=j[p]; if(esc){out+=c=='n'?' ':c;esc=false;}else if(c=='\\')esc=true;else if(c=='"')break;else out+=c;}
    return out.empty()?fallback:out;
}
double json_number(const std::string& j,const char* key) {
    std::string needle=std::string("\"")+key+"\""; auto p=j.find(needle);
    if(p==std::string::npos) return 0; p=j.find(':',p+needle.size()); if(p==std::string::npos)return 0;
    return std::atof(j.c_str()+p+1);
}
bool json_bool(const std::string& j,const char* key) {
    std::string needle=std::string("\"")+key+"\""; auto p=j.find(needle);
    if(p==std::string::npos)return false; p=j.find(':',p+needle.size());
    return p!=std::string::npos && j.find("true",p)<j.find_first_of(",}",p);
}
void set_text(lv_obj_t* obj,const std::string& s){if(obj)lv_label_set_text(obj,s.c_str());}
void command(const char* c){http_request("POST","/api/command",std::string("{\"command\":\"")+c+"\"}");}
void transport_event(lv_event_t* e){
    const int cmd=(int)(intptr_t)lv_event_get_user_data(e);
    if(cmd==0) command("previous");
    else if(cmd==1) command("toggle");
    else if(cmd==2) command("next");
    else if(cmd==3){page=(page+1)%3;}
    else if(cmd==4){sleep_minutes=sleep_minutes==0?15:sleep_minutes==15?30:sleep_minutes==30?60:0;sleep_remaining=sleep_minutes*60;}
}
lv_obj_t* button(lv_obj_t* p,const char* txt,int id,int w){
    auto* b=lv_button_create(p); lv_obj_set_size(b,w,25);
    lv_obj_set_style_radius(b,5,0);
    lv_obj_set_style_bg_color(b,lv_color_hex(0x252525),0);
    lv_obj_set_style_border_color(b,lv_color_hex(0xFF5500),0);
    lv_obj_set_style_border_width(b,1,0);
    lv_obj_add_event_cb(b,transport_event,LV_EVENT_CLICKED,(void*)(intptr_t)id);
    auto* l=lv_label_create(b);lv_label_set_text(l,txt);lv_obj_center(l);return b;
}
void poll_state(){
    auto j=http_request("GET","/api/state");
    if(j.empty()){connected=false;set_text(status_label,"PHONE OFFLINE  /  OPEN REMOTE");return;}
    connected=true;
    std::string title=json_string(j,"title","Nothing playing");
    std::string artist=json_string(j,"artist","Choose a track on your phone");
    playing=json_bool(j,"playing");\n    queue_count=(int)json_number(j,"queue_count");
    double pos=json_number(j,"position"), dur=json_number(j,"duration");
    set_text(title_label,title);set_text(artist_label,artist);
    set_text(status_label,playing?"●  PLAYING   /   PHONE LINKED":"Ⅱ  PAUSED   /   PHONE LINKED");
    if(progress_bar)lv_bar_set_value(progress_bar,dur>0?(int)std::clamp(pos/dur*1000.0,0.0,1000.0):0,LV_ANIM_OFF);
    char t[32]; std::snprintf(t,sizeof(t),"%02d:%02d  /  %02d:%02d",
        (int)pos/60000,((int)pos/1000)%60,(int)dur/60000,((int)dur/1000)%60);
    set_text(time_label,t);
}
void build_page(){
    if(page==0){
        set_text(page_label,"NOW PLAYING");
        lv_obj_clear_flag(title_label,LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(artist_label,LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(progress_bar,LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(time_label,LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(cover_mark,LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(sleep_label,LV_OBJ_FLAG_HIDDEN);
        set_text(sleep_label,"");
    }else if(page==1){
        set_text(page_label,"UP NEXT");
        set_text(title_label,"Queue lives on your phone");
        set_text(artist_label,"Open SoundCloud remote to browse tracks");
        set_text(sleep_label,"Use the phone to choose the next song.");
        lv_obj_add_flag(progress_bar,LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(time_label,LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(cover_mark,LV_OBJ_FLAG_HIDDEN);
    }else{
        set_text(page_label,"SLEEP MODE");
        set_text(title_label,"Sleep timer");
        set_text(artist_label,"Tap TIMER to cycle  OFF / 15 / 30 / 60 min");
        char b[48];std::snprintf(b,sizeof(b),"Timer: %s",sleep_minutes?std::to_string(sleep_remaining/60).append(" min").c_str():"OFF");
        set_text(sleep_label,b);
        lv_obj_add_flag(progress_bar,LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(time_label,LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(cover_mark,LV_OBJ_FLAG_HIDDEN);
    }
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
    auto* s=lv_obj_create(nullptr);lv_obj_remove_style_all(s);
    lv_obj_set_style_bg_color(s,lv_color_hex(0x080808),0);lv_obj_set_style_bg_opa(s,LV_OPA_COVER,0);
    lv_obj_clear_flag(s,LV_OBJ_FLAG_SCROLLABLE);
    auto* brand=lv_label_create(s);lv_label_set_text(brand,"CLOUDZERO");
    lv_obj_set_style_text_color(brand,lv_color_hex(0xFF5500),0);
    lv_obj_set_style_text_font(brand,&lv_font_montserrat_12,0);lv_obj_align(brand,LV_ALIGN_TOP_LEFT,8,5);
    page_label=lv_label_create(s);lv_obj_set_style_text_color(page_label,lv_color_hex(0xAAAAAA),0);
    lv_obj_set_style_text_font(page_label,&lv_font_montserrat_10,0);lv_obj_align(page_label,LV_ALIGN_TOP_RIGHT,-8,7);
    auto* line=lv_obj_create(s);lv_obj_remove_style_all(line);lv_obj_set_size(line,304,1);
    lv_obj_set_style_bg_color(line,lv_color_hex(0x333333),0);lv_obj_set_style_bg_opa(line,LV_OPA_COVER,0);lv_obj_align(line,LV_ALIGN_TOP_MID,0,23);
    auto* cover=lv_obj_create(s);lv_obj_set_size(cover,76,76);lv_obj_set_style_bg_color(cover,lv_color_hex(0x19110D),0);
    lv_obj_set_style_border_color(cover,lv_color_hex(0xFF5500),0);lv_obj_set_style_border_width(cover,2,0);lv_obj_align(cover,LV_ALIGN_TOP_RIGHT,-8,34);
    cover_mark=lv_label_create(cover);lv_label_set_text(cover_mark,"SC");lv_obj_set_style_text_color(cover_mark,lv_color_hex(0xFF5500),0);
    lv_obj_set_style_text_font(cover_mark,&lv_font_montserrat_24,0);lv_obj_center(cover_mark);
    title_label=lv_label_create(s);lv_obj_set_width(title_label,210);lv_label_set_long_mode(title_label,LV_LABEL_LONG_DOT);
    lv_obj_set_style_text_color(title_label,lv_color_hex(0xF4F4F4),0);lv_obj_set_style_text_font(title_label,&lv_font_montserrat_16,0);lv_obj_align(title_label,LV_ALIGN_TOP_LEFT,8,36);
    artist_label=lv_label_create(s);lv_obj_set_width(artist_label,210);lv_label_set_long_mode(artist_label,LV_LABEL_LONG_DOT);
    lv_obj_set_style_text_color(artist_label,lv_color_hex(0x999999),0);lv_obj_set_style_text_font(artist_label,&lv_font_montserrat_12,0);lv_obj_align(artist_label,LV_ALIGN_TOP_LEFT,8,59);
    progress_bar=lv_bar_create(s);lv_obj_set_size(progress_bar,210,5);lv_bar_set_range(progress_bar,0,1000);
    lv_obj_set_style_bg_color(progress_bar,lv_color_hex(0x333333),LV_PART_MAIN);lv_obj_set_style_bg_color(progress_bar,lv_color_hex(0xFF5500),LV_PART_INDICATOR);
    lv_obj_align(progress_bar,LV_ALIGN_TOP_LEFT,8,84);
    time_label=lv_label_create(s);lv_obj_set_style_text_color(time_label,lv_color_hex(0x777777),0);lv_obj_set_style_text_font(time_label,&lv_font_montserrat_10,0);lv_obj_align(time_label,LV_ALIGN_TOP_LEFT,8,91);
    sleep_label=lv_label_create(s);lv_obj_set_style_text_color(sleep_label,lv_color_hex(0xFF8844),0);lv_obj_set_style_text_font(sleep_label,&lv_font_montserrat_10,0);lv_obj_align(sleep_label,LV_ALIGN_TOP_LEFT,8,91);
    auto* controls=lv_obj_create(s);lv_obj_remove_style_all(controls);lv_obj_set_size(controls,210,27);lv_obj_align(controls,LV_ALIGN_TOP_LEFT,8,108);
    lv_obj_set_flex_flow(controls,LV_FLEX_FLOW_ROW);lv_obj_set_flex_align(controls,LV_FLEX_ALIGN_SPACE_BETWEEN,LV_FLEX_ALIGN_CENTER,LV_FLEX_ALIGN_CENTER);
    button(controls,"|<",0,42);button(controls,"PLAY",1,72);button(controls,">|",2,42);
    auto* nav=lv_obj_create(s);lv_obj_remove_style_all(nav);lv_obj_set_size(nav,82,28);lv_obj_align(nav,LV_ALIGN_TOP_RIGHT,-5,112);
    button(nav,"VIEW",3,76);
    status_label=lv_label_create(s);lv_label_set_text(status_label,"CONNECTING TO PHONE...");
    lv_obj_set_style_text_color(status_label,lv_color_hex(0x777777),0);lv_obj_set_style_text_font(status_label,&lv_font_montserrat_10,0);lv_obj_align(status_label,LV_ALIGN_BOTTOM_LEFT,8,-5);
    lv_screen_load(s);build_page();
    uint32_t last=0;
    while(true){
        lv_timer_handler();
        if(lv_tick_get()-last>900){last=lv_tick_get();poll_state();build_page();}
        lv_delay_ms(5);
    }
    return 0;
#endif
}
}
