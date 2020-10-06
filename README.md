# HTTPServer
Simple thread pool http server.
## Run
```
$ python httpd.py -h [host] -p [port] -w [n workers] -r [document root dir]
```
## Benchmark
```
$ ab -n 50000 -c 100 -r http://localhost:8080/

This is ApacheBench, Version 2.3 <$Revision: 1879490 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        HTTPServer/1.0
Server Hostname:        localhost
Server Port:            8080

Document Path:          /
Document Length:        146 bytes

Concurrency Level:      100
Time taken for tests:   50.130 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      14550000 bytes
HTML transferred:       7300000 bytes
Requests per second:    997.41 [#/sec] (mean)
Time per request:       100.260 [ms] (mean)
Time per request:       1.003 [ms] (mean, across all concurrent requests)
Transfer rate:          283.44 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.4      0       3
Processing:    12   96  31.5     92     312
Waiting:        7   80  28.8     77     283
Total:         12   96  31.5     93     312

Percentage of the requests served within a certain time (ms)
  50%     93
  66%    106
  75%    115
  80%    121
  90%    138
  95%    153
  98%    171
  99%    185
 100%    312 (longest request)
```