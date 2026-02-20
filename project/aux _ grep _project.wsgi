[0;1;32m●[0m nginx.service - A high performance web server and a reverse proxy server
     Loaded: loaded (]8;;file://Igor-Bar/usr/lib/systemd/system/nginx.service/usr/lib/systemd/system/nginx.service]8;;; [0;1;32menabled[0m; preset: [0;1;32menabled[0m)
     Active: [0;1;32mactive (running)[0m since Tue 2026-02-10 09:58:26 UTC; 3min 20s ago
       Docs: ]8;;man:nginx(8)man:nginx(8)]8;;
    Process: 774502 ExecStartPre=/usr/sbin/nginx -t -q -g daemon on; master_process on; (code=exited, status=0/SUCCESS)
    Process: 774506 ExecStart=/usr/sbin/nginx -g daemon on; master_process on; (code=exited, status=0/SUCCESS)
   Main PID: 774507 (nginx)
      Tasks: 3 (limit: 4540)
     Memory: 2.4M (peak: 2.9M)
        CPU: 19ms
     CGroup: /system.slice/nginx.service
             ├─[0;38;5;245m774507 "nginx: master process /usr/sbin/nginx -g daemon on; master_process on;"[0m
             ├─[0;38;5;245m774508 "nginx: worker process"[0m
             └─[0;38;5;245m774509 "nginx: worker process"[0m

Feb 10 09:58:26 Igor-Bar systemd[1]: Starting nginx.service - A high performance web server and a reverse proxy server...
Feb 10 09:58:26 Igor-Bar systemd[1]: Started nginx.service - A high performance web server and a reverse proxy server.
