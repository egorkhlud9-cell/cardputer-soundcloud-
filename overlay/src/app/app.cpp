/*
 * SPDX-License-Identifier: MIT
 * CloudZero - standalone on-device SoundCloud player shell.
 *
 * The local CloudZero UI runs in the Cardputer Zero's installed QtWebKit
 * browser. This keeps the application self-contained on the device while
 * using SoundCloud's official HTML5 Widget for public-track playback.
 * Never use this browser for entering account passwords or other secrets.
 */
#include "app.h"
#include <cstdio>
#include <cstdlib>
#include <unistd.h>

namespace app {
int Application::run() {
    // The local service is enabled by the Debian package. No phone or remote
    // browser participates in playback or library management.
    if (access("/usr/bin/zero-browser", X_OK) != 0) {
        std::fprintf(stderr,
            "CloudZero needs Zero Browser with the QtWebKit engine installed.\n"
            "Install/enable Zero Browser, then launch CloudZero again.\n");
        return 127;
    }

    execl("/usr/bin/zero-browser",
          "zero-browser",
          "--mode", "qtwebkit",
          "--url", "http://127.0.0.1:8766/",
          static_cast<char *>(nullptr));

    std::perror("CloudZero: could not start Zero Browser");
    return 127;
}
}
