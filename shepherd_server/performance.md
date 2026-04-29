# Performance-Analysis

## Scheduler Overhead

Baseline are the timings each user gets via mail:

```
t_overhead = t_finished - t_scheduled - duration
```

- before > 5 min per experiment
- v2025.08.1 - < 3 min
- v2026.02.2 - 3:47 -> sheep takes ~27s for each start
- v2026.04.2 - 2:45 -> BUG: sheep ignore scheduled start-time
    - pre: 149 s; sheep needs 21s till idle-wait
    - post: 16 s ???
- v2026.04.x - 3:00
    - pre 137 s, sheeps needs 21s till idle-wait, and waits 37s => 60 s wanted, (now 45)
    - post 43 s, between completion & herd_fetch_logs() is a 30s (now 20s) wait
- sleeps changes in scheduler
    - completion-wait (prep-xp)		11 -> 5 s
    - completion-wait (clean-herd)	8 -> 5 s
    - post-prep - stabilize			30 -> 10 s
    - sync   						60 -> 50 s (~21 s of that are non-idle for the sheep)
    - completion-wait (xp) 			21 -> 5 s
    - post-xp						30 -> 20 s
    - scheduler idle-wait		    20 -> 5 s (decoupled updating status)
    - minimum idle-wait - before: 120 s, now: 85 s
- v2026.04.x - 2:06
    pre 105 s
    post 21 s
- there is still a bug that lets sheep exit early
