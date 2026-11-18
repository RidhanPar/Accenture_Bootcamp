# Decision Log: Local RAG Pipeline


## Machine
- **Hardware:** CPU - 1 RAM - 16 GB native Ollama
- **`ollama ps` with my main model loaded:**
NAME                       ID              SIZE      PROCESSOR    CONTEXT            
qwen3.5:4b-q4_K_M          d8b0f5e9760c    3.4 GB    100% CPU     8192       
nomic-embed-text:latest    0a109f422b47    389 MB    100% CPU     2048           


## Model Selection
- **Chosen LLM:** qwen3.5:4b-q4_K_M
- **Thinking:** off - when I checked the benchmark restults both the models worked well and scored well even without thinking so thinking will take unecessary time that increase the latency so I planned to work with the model thinking turned off
- **Why:** I have choosed 2B parameter model first because when comparing the benchmark results in terms of quality both models performed well, then I have checked with the speed this model performed faster by 2 times than the 4b parameter model for rag related questions.The 2B averages 12.8 s per prompt against 24.7 s for the 4B (4.7 vs 2.6 tokens per second). At the same time small loss of quality it performed low on the summerization category in terms of quality still it worked better when comes to rag specific bechmarks so here I choose speed since the quality is almost same.However,after getting the results from my v2 rag pipeline I were able to see that the retrival part was good but the model is not correctly generating it therefore I have switched again to 4B model.
- **What I considered but rejected:** I have not considered any other model.


## Embedding Model
- **Chosen:** nomic-embed-text, 768
- **Why:** I have not compared anyother embedding models once I checked my pipeline v1 resutls I see that the chunks are ranked well and the issue are mostly with the boundries of the chunks so, I felt no change might be needed here.


## Parsing
- **Extractor:** I  have used the "pypdf" as the extracter and when I did that normally the table was extracted as a continues text without any layout, that become one of the cause in wrong answer for q07 so I later enabled the paratmeter with layout on pypdf it worked well however the reason for q07 is not only that it is also missing the table header that was from the previous cut on chunk boundaries for that the parent child startergy fix worked.
Table Before:
-**Before**
Starter 99.5% ~3 hours 39 minutes Calendar month\nProfessional 99.9% ~43 minutes Calendar month\nTier Uptime SLA Maximum Monthly Downtime Measurement\nEnterprise 99.95% ~21 minutes Calendar month\n7.2 SLA Credits\nIf NovaTech fails to meet the uptime commitment, customers are eligible for\nservice credits:\nUptime Achieved Starter Credit Professional Credit Enterprise Credit\n99.0% - 99.49% 5% — —\n98.0% - 99.89% — 10% —\n99.9% - 99.94% — — 10%\n95.0% - 98.99% — 15% —\n99.0% - 99.89% — — 20%\nBelow 95.0% 10% 25% 30%"
**After**
Service Level Agreements\n\nNovaTech provides uptime guarantees based on tier. Uptime is measured\nmonthly and excludes scheduled maintenance windows (announced at least 72\nhours in advance, limited to 4 hours per month).\n\n7.1 Uptime Commitments\n\n  Tier   Uptime SLA   Maximum Monthly Downtime   Measurement\n\n  Starter   99.5%   ~3 hours 39 minutes   Calendar month\n\n  Professional   99.9%   ~43 minutes   Calendar month\n\nTier   Uptime SLA   Maximum Monthly Downtime   Measurement\n\n  Enterprise   99.95%   ~21 minutes   Calendar month


## Chunking Strategy
- **Chunk size:**
  - V1: 512 characters
  - V2 & finalversion child: 400 characters (what gets embedded and searched)
  - V2 & finalversion child parent: one section, split at headings like "7. Service Level Agreement", capped at max 2500 characters the splitter looks for the numbered headings and split.
- **Overlap:**
  - V1: 50 characters
  - V2 & finalversion child child: 50 characters
  - V2 & finalversion child parent: merge threshold min 300 character and  max 2500 character with 200 character overlap
- **Why:** I have changed the chunking startergy becuase most of the answers wrong were due to cut boundries therefore since this documents are structured and having the important part at end of the section and the definition that makes the LLM found the match at the start its like for the meeting notes the agenda at start and conlusion or decision is at the end and it missed due to the chunking startergy of V1 and I have changed the startergy to Parent child since the document is structured this startergy will return the entire info of that section matching our chunks to the context so the informaiton won't me missed here.


## Retrieval Configuration
- **Top-K:**
  - V1: top 5 chunks of 512 characters
  - V2 & finalversion child: search the top 20 child chunks, return the top 4 unique parent sections (max 2500 characters each)
- **Context window:** 8192 tokens (from `ollama ps`)
    - V1 prompt_tokens: 612 to 955 (`pipeline_outputs_v1.json`)
    - V2 with 2B model prompt_tokens: 994 to 2,325 (`pipeline_outputs_v2.json`)
    - V3 with 4B model prompt_tokens: 1,171 to 2,502 (`pipeline_outputs.json`)
- **Why:**
  I have changed the strategy to parent child chunking so that we do not miss the correct chunks or lose important chunks that are cut off at chunk boundaries.So, I first thought about increasing the chunk size, but we could not be sure which number would work best, and we might mix several other topics into a single chunk, which would create conflicts for the model. So I made the change to retrieve the top 20 child chunks and, from those, return the top 4 unique parents, each with a maximum of 2500 characters. This is still within our context size, and it seems it doesn't affected the speed much. This decision was taken mainly because of q06, q10, q12 and q13, which failed because important chunks were missing due to the cutoff. That is why I changed the strategy, and also the configuration to suit that strategy.


## Observations
- **What worked well:** Initially, The 2B model did well and it generated the answers for the questions as we instructed on our prompt, after the v2 fixes the context were retrived fixed most of the issues but still due to model not able to generate properly I have choosen to go with 4B parameter model.
- **What failed:** With my version 1 setup I have used the overlap small chunks startergy that missed some important parts resulted in invented and wrong answers for question q06,q10,q12 and q13 since it was written in some structure mostly when with the meeting logs it just interpert the important parts from the question and missed the decsion part. Another thing is table data the pdf missed the table layout resulted in wrong answer for q07, and q01,02 had some formatting issues as section 1 instead of source 1 . Other than this q14 had an issue with finding the recent informaiton there was a date conflict that the model took the first chunk since it doen't know which comes first
- **Traps I hit:** Here what I saw is missing important parts and since it is under some same paragraph the conclusions are at the end but the definition is at the start so the chunking startergy retrive the start and the acutall answer lies on the end not retrived , So  I decided to use parent children statergy that we learned from out previous class since the documents are in structured format. for this q07 I made changes in the extraction so that the table are retrieved with its layout.For q01,q02 I have made some changes in the prompt that can handle teh issues that I have gone through in areas where the right chunk retrived but answer was not fullfilled, for q14 I have made a fix by including the date of the document in the context
- **Local vs cloud expectations:** I will say the cloud will work much faster since it has the GPU on their own and then I would say that the failed questions due to the right chunck retrived but missed some parts with low reasoning effort this can be also fixed and the score will be 18/18 


## If I Had More Time / Better Hardware
- If I would have more time may be I tried experimenting with the something what we can do to reduce the latency without compramising quality because now quality is doing very well, I have may have did some changes with the max parent characters and top K and see if this improves the speed and also add a GPU which make might influence the speed here.


