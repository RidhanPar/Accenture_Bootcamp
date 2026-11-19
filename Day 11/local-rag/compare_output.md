## Local vs cloud

Sources: eval_results_local.json, eval_results_cloud.json, pipeline_outputs_local.json, pipeline_outputs_cloud.json. Mean ± 2 × SE, SE = standard deviation / √n.

| Metric | n | Local | Cloud | Cloud − local (per question) | Verdict |
|---|---|---|---|---|---|
| Contextual Relevancy | 18 | 0.28 ± 0.13 | 0.35 ± 0.13 | 0.07 ± 0.05 | cloud higher |
| Contextual Recall | 18 | 0.86 ± 0.16 | 0.86 ± 0.16 | 0.00 ± 0.00 | no clear difference |
| Contextual Precision | 18 | 0.97 ± 0.03 | 0.92 ± 0.11 | -0.05 ± 0.10 | no clear difference |
| Faithfulness | 18 | 0.81 ± 0.12 | 0.64 ± 0.21 | -0.17 ± 0.21 | no clear difference |
| Answer Relevancy | 18 | 0.93 ± 0.08 | 0.85 ± 0.13 | -0.07 ± 0.14 | no clear difference |

| Run | Model | Median generation (s) | Slowest generation (s) | Avg prompt tokens | Avg completion tokens | Empty or failed answers | Cost (list price) |
|---|---|---|---|---|---|---|---|
| local (first call dropped: model load) | qwen3.5:4b-q4_K_M | 99.7 | 150.9 | 1795 | 121 | 0 | local hardware, no per-token cost |
| cloud | gpt-5.6-luna | 1.5 | 4.0 | 1662 | 52 | 0 | not set |

Unanswerable questions, string check for "cannot find this information":

| Run | Refused with the exact sentence | Questions |
|---|---|---|
| local | 0 of 3 | none |
| cloud | 3 of 3 | q16, q17, q18 |

| Run | Passed by hand | Failed by hand |
|---|---|---|
| local | 16 of 18 | q13, q14 |
| cloud | 17 of 18 | q14 |

Judge vs hand rating. Judge pass = Faithfulness and Answer Relevancy both >= 0.7. Hand pass = `passed` in pipeline_outputs_<label>.json.

| Run | Both pass | Both fail | Judge passes, I failed | Judge fails, I passed |
|---|---|---|---|---|
| local | 11 (q01, q02, q03, q04, q05, q07, q08, q09, q10, q11, q15) | 1 (q14) | 1 (q13) | 5 (q06, q12, q16, q17, q18) |
| cloud | 7 (q01, q03, q04, q05, q08, q09, q10) | 0 | 1 (q14) | 10 (q02, q06, q07, q11, q12, q13, q15, q16, q17, q18) |
