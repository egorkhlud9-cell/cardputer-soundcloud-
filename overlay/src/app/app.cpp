/*
 * SPDX-License-Identifier: MIT
 * CloudZero - CardputerZero SoundCloud companion UI.
 */
#include "app.h"
#include "linux_input.h"
#include "lvgl.h"
#if !USE_DESKTOP
#include "src/drivers/display/fb/lv_linux_fbdev.h"
#endif
#ifndef APP_FRAMEBUFFER_DEVICE
#define APP_FRAMEBUFFER_DEVICE "/dev/fb0"
#endif
namespace app {
namespace {
lv_obj_t* title_label = nullptr;
lv_obj_t* status_label = nullptr;
bool playing = false;
void set_label(lv_obj_t* label, const char* value) {
    if (label) lv_label_set_text(label, value);
}
void transport_event(lv_event_t* event) {
    const auto command = static_cast<int>(reinterpret_cast<intptr_t>(lv_event_get_user_data(event)));
    if (command == 0) playing = !playing;
    if (command == 1 || command == 2) set_label(title_label, "Waiting for phone...");
    set_label(status_label, playing ? "PHONE REMOTE  |  PLAYING" : "PHONE REMOTE  |  PAUSED");
}
lv_obj_t* make_button(lv_obj_t* parent, const char* text, int command, int width) {
    auto* button = lv_button_create(parent);
    lv_obj_set_size(button, width, 30);
    lv_obj_add_event_cb(button, transport_event, LV_EVENT_CLICKED,
                        reinterpret_cast<void*>(static_cast<intptr_t>(command)));
    auto* label = lv_label_create(button);
    lv_label_set_text(label, text);
    lv_obj_center(label);
    return button;
}
}
int Application::run() {
    lv_init();
#if USE_DESKTOP
    return 2;
#else
    auto* display = lv_linux_fbdev_create();
    if (!display || lv_linux_fbdev_set_file(display, APP_FRAMEBUFFER_DEVICE) != LV_RESULT_OK) return 1;
    platform::init_key_input(display);
    auto* screen = lv_obj_create(nullptr);
    lv_obj_remove_style_all(screen);
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x090909), 0);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);
    lv_obj_clear_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
    auto* header = lv_label_create(screen);
    lv_label_set_text(header, "CLOUDZERO  /  SOUNDCLOUD");
    lv_obj_set_style_text_color(header, lv_color_hex(0xFF5500), 0);
    lv_obj_set_style_text_font(header, &lv_font_montserrat_12, 0);
    lv_obj_align(header, LV_ALIGN_TOP_LEFT, 8, 5);
    auto* divider = lv_obj_create(screen);
    lv_obj_remove_style_all(divider);
    lv_obj_set_size(divider, 304, 1);
    lv_obj_set_style_bg_color(divider, lv_color_hex(0x383838), 0);
    lv_obj_set_style_bg_opa(divider, LV_OPA_COVER, 0);
    lv_obj_align(divider, LV_ALIGN_TOP_MID, 0, 23);
    title_label = lv_label_create(screen);
    lv_label_set_text(title_label, "Connect your phone");
    lv_obj_set_style_text_color(title_label, lv_color_hex(0xF2F2F2), 0);
    lv_obj_set_style_text_font(title_label, &lv_font_montserrat_16, 0);
    lv_label_set_long_mode(title_label, LV_LABEL_LONG_DOT);
    lv_obj_set_width(title_label, 210);
    lv_obj_align(title_label, LV_ALIGN_TOP_LEFT, 8, 38);
    auto* artist = lv_label_create(screen);
    lv_label_set_text(artist, "Open CloudZero remote on Wi-Fi");
    lv_obj_set_style_text_color(artist, lv_color_hex(0x999999), 0);
    lv_obj_set_style_text_font(artist, &lv_font_montserrat_12, 0);
    lv_label_set_long_mode(artist, LV_LABEL_LONG_DOT);
    lv_obj_set_width(artist, 210);
    lv_obj_align(artist, LV_ALIGN_TOP_LEFT, 8, 61);
    auto* art = lv_obj_create(screen);
    lv_obj_set_size(art, 76, 76);
    lv_obj_set_style_bg_color(art, lv_color_hex(0x191919), 0);
    lv_obj_set_style_border_color(art, lv_color_hex(0xFF5500), 0);
    lv_obj_set_style_border_width(art, 1, 0);
    lv_obj_align(art, LV_ALIGN_TOP_RIGHT, -8, 36);
    auto* art_mark = lv_label_create(art);
    lv_label_set_text(art_mark, "SC");
    lv_obj_set_style_text_color(art_mark, lv_color_hex(0xFF5500), 0);
    lv_obj_set_style_text_font(art_mark, &lv_font_montserrat_24, 0);
    lv_obj_center(art_mark);
    auto* progress = lv_bar_create(screen);
    lv_obj_set_size(progress, 210, 5);
    lv_bar_set_range(progress, 0, 1000);
    lv_bar_set_value(progress, 0, LV_ANIM_OFF);
    lv_obj_set_style_bg_color(progress, lv_color_hex(0x333333), LV_PART_MAIN);
    lv_obj_set_style_bg_color(progress, lv_color_hex(0xFF5500), LV_PART_INDICATOR);
    lv_obj_align(progress, LV_ALIGN_TOP_LEFT, 8, 91);
    auto* controls = lv_obj_create(screen);
    lv_obj_remove_style_all(controls);
    lv_obj_set_size(controls, 210, 34);
    lv_obj_align(controls, LV_ALIGN_TOP_LEFT, 8, 105);
    lv_obj_set_flex_flow(controls, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(controls, LV_FLEX_ALIGN_SPACE_BETWEEN, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    make_button(controls, "|<", 1, 48);
    make_button(controls, "PLAY", 0, 76);
    make_button(controls, ">|", 2, 48);
    status_label = lv_label_create(screen);
    lv_label_set_text(status_label, "PHONE REMOTE  |  NOT CONNECTED");
    lv_obj_set_style_text_color(status_label, lv_color_hex(0x888888), 0);
    lv_obj_set_style_text_font(status_label, &lv_font_montserrat_10, 0);
    lv_obj_align(status_label, LV_ALIGN_BOTTOM_LEFT, 8, -5);
    lv_screen_load(screen);
    while (true) {
        lv_timer_handler();
        lv_delay_ms(5);
    }
    return 0;
#endif
}
}
