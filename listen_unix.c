#define _GNU_SOURCE

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/un.h>
#include <arpa/inet.h>
#include <dlfcn.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <errno.h>

int bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen) {
    static int (*orig)(int, const struct sockaddr *, socklen_t);
    if (!orig) {
        orig = dlsym(RTLD_NEXT, "bind");
    }

    if (addr->sa_family == AF_INET6) {
        const struct sockaddr_in6 *addr_in6 = (const struct sockaddr_in6 *)addr;
        if (addr_in6->sin6_port == htons(80) && memcmp(&addr_in6->sin6_addr, &in6addr_any, sizeof(struct in6_addr)) == 0) {
            struct sockaddr_un addr_un = {
                .sun_family = AF_UNIX,
                .sun_path = "/usr/local/apache2/sock_dir/listen.sock",
            };
            unsetenv("LD_PRELOAD");
            close(sockfd);

            int fd = socket(AF_UNIX, SOCK_STREAM|SOCK_CLOEXEC, 0);
            if (fd == -1) {
                abort();
            }

            if (fd != sockfd) {
                if (dup3(fd, sockfd, O_CLOEXEC) == -1) {
                    abort();
                }

                close(fd);
            }
            if (unlink(addr_un.sun_path) != 0 && errno != ENOENT) {
                abort();
            }

            int ret = orig(sockfd, (const struct sockaddr*)&addr_un, sizeof(addr_un));
            if (ret == 0) {
                chmod(addr_un.sun_path, S_IRUSR | S_IWUSR | S_IXUSR | S_IRGRP | S_IWGRP | S_IXGRP | S_IXOTH | S_IROTH | S_IWOTH);
            }
            return ret;
        }
    }
    return orig(sockfd, addr, addrlen);
}
