/* VFE — IPC bridge implementation  (original C99) */
#include "ipc.h"
#include "../libs/cjson.h"
#include "../core/log.h"
#include "../scene/scene.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

#ifdef _WIN32
#  include <io.h>
#  define STDIN_FD  0
#else
#  include <unistd.h>
#  include <sys/socket.h>
#  include <sys/un.h>
#  include <fcntl.h>
#  include <sys/select.h>
#  define STDIN_FD  STDIN_FILENO
#endif

bool vfe_ipc_init(VFE_IPC *ipc, World *w, VFE_Window *win,
                  VFE_LuaVM *lua, bool use_socket,
                  const char *socket_path) {
    memset(ipc, 0, sizeof(*ipc));
    ipc->world       = w;
    ipc->win         = win;
    ipc->lua         = lua;
    ipc->use_socket  = use_socket;
    ipc->socket_fd   = -1;
    ipc->client_fd   = -1;
    ipc->running     = true;

#ifndef _WIN32
    if (use_socket && socket_path) {
        strncpy(ipc->socket_path, socket_path, sizeof(ipc->socket_path)-1);
        ipc->socket_fd = socket(AF_UNIX, SOCK_STREAM, 0);
        if (ipc->socket_fd < 0) {
            VFE_ERROR("IPC socket: %s", strerror(errno));
            return false;
        }
        unlink(socket_path);
        struct sockaddr_un addr = {0};
        addr.sun_family = AF_UNIX;
        strncpy(addr.sun_path, socket_path, sizeof(addr.sun_path)-1);
        if (bind(ipc->socket_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0 ||
            listen(ipc->socket_fd, 1) < 0) {
            VFE_ERROR("IPC bind/listen: %s", strerror(errno));
            return false;
        }
        /* Non-blocking accept */
        fcntl(ipc->socket_fd, F_SETFL, O_NONBLOCK);
        VFE_INFO("IPC listening on %s", socket_path);
    } else {
        /* stdin non-blocking */
        fcntl(STDIN_FD, F_SETFL, O_NONBLOCK);
        VFE_INFO("IPC: stdin/stdout mode");
    }
#else
    VFE_INFO("IPC: stdin/stdout mode (Windows)");
#endif
    return true;
}

void vfe_ipc_close(VFE_IPC *ipc) {
#ifndef _WIN32
    if (ipc->client_fd >= 0) { close(ipc->client_fd); ipc->client_fd = -1; }
    if (ipc->socket_fd >= 0) { close(ipc->socket_fd); ipc->socket_fd = -1; }
    if (ipc->socket_path[0]) unlink(ipc->socket_path);
#endif
}

static void ipc_send(VFE_IPC *ipc, cJSON *resp) {
    char *s = cJSON_PrintUnformatted(resp);
    if (!s) return;
    int fd = (ipc->client_fd >= 0) ? ipc->client_fd : STDOUT_FILENO;
    dprintf(fd, "%s\n", s);
    free(s);
}

static cJSON *dispatch(VFE_IPC *ipc, cJSON *req) {
    const char *cmd = "";
    cJSON *cmd_j = cJSON_GetObjectItem(req, "cmd");
    if (cmd_j && cmd_j->valuestring) cmd = cmd_j->valuestring;
    cJSON *args = cJSON_GetObjectItem(req, "args");

    cJSON *resp = cJSON_CreateObject();

    if (strcmp(cmd, "spawn") == 0) {
        EntityID id = vfe_entity_create(ipc->world);
        if (id != VFE_INVALID_ENTITY) {
            TransformComponent *t = (TransformComponent *)
                vfe_comp_add(ipc->world, id, VFE_COMP_TRANSFORM);
            t->scale.x = t->scale.y = t->scale.z = 1.0f;
        }
        cJSON_AddStringToObject(resp,"status","ok");
        cJSON_AddNumberToObject(resp,"entity",(double)id);

    } else if (strcmp(cmd, "destroy") == 0) {
        EntityID id = args ?
            (EntityID)cJSON_GetNumberValue(cJSON_GetObjectItem(args,"entity")) : 0;
        vfe_entity_destroy(ipc->world, id);
        cJSON_AddStringToObject(resp,"status","ok");

    } else if (strcmp(cmd, "set_pos") == 0) {
        if (args) {
            EntityID id = (EntityID)cJSON_GetNumberValue(cJSON_GetObjectItem(args,"entity"));
            float x=(float)cJSON_GetNumberValue(cJSON_GetObjectItem(args,"x"));
            float y=(float)cJSON_GetNumberValue(cJSON_GetObjectItem(args,"y"));
            float z=(float)cJSON_GetNumberValue(cJSON_GetObjectItem(args,"z"));
            TransformComponent *t = VFE_TRANSFORM(ipc->world, id);
            if (t) { t->position.x=x; t->position.y=y; t->position.z=z; }
        }
        cJSON_AddStringToObject(resp,"status","ok");

    } else if (strcmp(cmd, "set_vel") == 0) {
        if (args) {
            EntityID id = (EntityID)cJSON_GetNumberValue(cJSON_GetObjectItem(args,"entity"));
            float x=(float)cJSON_GetNumberValue(cJSON_GetObjectItem(args,"x"));
            float y=(float)cJSON_GetNumberValue(cJSON_GetObjectItem(args,"y"));
            float z=(float)cJSON_GetNumberValue(cJSON_GetObjectItem(args,"z"));
            RigidBodyComponent *rb = VFE_RIGIDBODY(ipc->world, id);
            if (rb) { rb->velocity.x=x; rb->velocity.y=y; rb->velocity.z=z; }
        }
        cJSON_AddStringToObject(resp,"status","ok");

    } else if (strcmp(cmd, "load_scene") == 0) {
        const char *path = args ?
            cJSON_GetStringValue(cJSON_GetObjectItem(args,"path")) : NULL;
        if (path) {
            vfe_scene_clear(ipc->world);
            bool ok = vfe_scene_load(ipc->world, path, NULL);
            cJSON_AddStringToObject(resp,"status", ok ? "ok" : "error");
        } else {
            cJSON_AddStringToObject(resp,"status","error");
            cJSON_AddStringToObject(resp,"message","path required");
        }

    } else if (strcmp(cmd, "screenshot") == 0) {
        const char *path = args ?
            cJSON_GetStringValue(cJSON_GetObjectItem(args,"path")) : "/tmp/vfe_shot.png";
        bool ok = vfe_window_screenshot(ipc->win, path ? path : "/tmp/vfe_shot.png");
        cJSON_AddStringToObject(resp,"status", ok ? "ok" : "error");
        cJSON_AddStringToObject(resp,"path",   path ? path : "");

    } else if (strcmp(cmd, "exec_lua") == 0) {
        const char *code = args ?
            cJSON_GetStringValue(cJSON_GetObjectItem(args,"code")) : NULL;
        bool ok = code ? vfe_lua_exec_string(ipc->lua, code) : false;
        cJSON_AddStringToObject(resp,"status", ok ? "ok" : "error");

    } else if (strcmp(cmd, "get_state") == 0) {
        cJSON_AddStringToObject(resp,"status","ok");
        cJSON_AddNumberToObject(resp,"entity_count",(double)ipc->world->entity_count);
        cJSON_AddNumberToObject(resp,"highest_id",  (double)ipc->world->highest_id);

    } else if (strcmp(cmd, "exit") == 0) {
        ipc->running = false;
        ipc->win->should_close = true;
        cJSON_AddStringToObject(resp,"status","ok");

    } else {
        cJSON_AddStringToObject(resp,"status","error");
        cJSON_AddStringToObject(resp,"message","unknown command");
    }
    return resp;
}

bool vfe_ipc_poll(VFE_IPC *ipc) {
    if (!ipc->running) return false;

#ifndef _WIN32
    /* Try to accept a new client on socket */
    if (ipc->use_socket && ipc->socket_fd >= 0 && ipc->client_fd < 0) {
        int c = accept(ipc->socket_fd, NULL, NULL);
        if (c >= 0) {
            fcntl(c, F_SETFL, O_NONBLOCK);
            ipc->client_fd = c;
            VFE_DEBUG("IPC client connected");
        }
    }

    int read_fd = (ipc->client_fd >= 0) ? ipc->client_fd : STDIN_FD;
    fd_set fds; FD_ZERO(&fds); FD_SET(read_fd, &fds);
    struct timeval tv = {0, 0};   /* non-blocking */
    if (select(read_fd+1, &fds, NULL, NULL, &tv) <= 0) return true;
#endif

    /* Read one line */
    char line[4096] = {0};
    int fd = (ipc->client_fd >= 0) ? ipc->client_fd : STDIN_FD;
    ssize_t n = read(fd, line, sizeof(line)-1);
    if (n <= 0) {
        if (ipc->client_fd >= 0) { close(ipc->client_fd); ipc->client_fd = -1; }
        return true;
    }
    line[n] = '\0';

    /* Parse and dispatch */
    cJSON *req = cJSON_Parse(line);
    if (req) {
        cJSON *resp = dispatch(ipc, req);
        ipc_send(ipc, resp);
        cJSON_Delete(resp);
        cJSON_Delete(req);
    }
    return ipc->running;
}
