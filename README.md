2fapache
========

Uses some horrible Apache features and `pam_oath` to implement 2fa in the web
server. Original idea was to get a free pen-test of this stuff before
deploying it on my own web-server. After all the bugs and weird *features* I ran
into, there's no chance I'll ever deploy this to a production system, ever.

Runs in a docker container with user namespaces. Just uses /home and file
system permissions in the container to store user data, with standard HTTP verbs
to create/edit/delete files. I didn't think things through and allowed (very
easily) deleting or overwriting flags. That kind of breaks the game-theory of
A/D CTFs (turning them into a race on who's first to exploit), so it shouldn't
have been possible.

Vuln
----

This service was more about finding a work fix, than about finding an exploit.
Exploiting was incredibly easy, only delayed a bit by the need to parse QR codes
encoded as UTF-8. I don't believe this worked out very well (at least some teams
ended up fingerprinting the checker), so I certainly won't do that again.

1. Originally, I didn't really have any good ideas for a vuln (next time I'll
   start with one first, again). So I came up with a lame logic error: when user
   X requests data of user Y, permissions are dropped to user Y instead of user
   X, circumventing the file permission check in the kernel. The fix is to
   change the `seteuid` call to drop permissions to those of user X (i.e.
   `env['REMOTE_USER']`).
2. When testing the fix for (1), I noticed that wouldn't work and every user
   still had access to every file owned by another user - a lucky accidental
   vulnerability. After some debugging, I found the error: I felt the need to
   optimize `dav_GET` by lazily returning file contents using `yield`. That
   function call is surrounded by calls to `seteuid(x)` and `seteuid(0)` to drop
   permissions. Of course, actual evaluation of the contents of the `yield`
   statement are forced much later somewhere in the `wsgi` framework. Therefore,
   the `open` call in `dav_GET` ended up being done by root - another reason why
   everyone with an account could access all files, whether they should've been
   able to or not.


Together, the intended fix looked something like this:

```diff
--- a/dist_root/srv/two-factor-apache/cgi-bin/app/dav.py
+++ b/dist_root/srv/two-factor-apache/cgi-bin/app/dav.py
@@ -145,12 +145,17 @@ def dav_responder(env, start_response):
 
     path = join(pw.pw_dir, path)
 
+    try:
+        pw = getpwnam(env['REMOTE_USER'])
+    except KeyError:
+        start_response(b'404 Not Found', [])
+        return []
     setegid(pw.pw_gid)
     seteuid(pw.pw_uid)
 
     try:
         if env['REQUEST_METHOD'] == 'GET':
-            return dav_GET(path, env, start_response)
+            return list(dav_GET(path, env, start_response))
         elif env['REQUEST_METHOD'] == 'HEAD':
             dav_HEAD(path, env, start_response)
             return []
```
