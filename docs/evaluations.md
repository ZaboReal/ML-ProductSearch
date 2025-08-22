## Mini Evaluation Results

### Latency Summary

| Backend   | Avg (ms) | P95 (ms) |
|-----------|----------|----------|
| Pinecone  | 76.84    | 149.66   |
| pgvector  | 15.98    | 46.37    |

### Precision@5 (manual)

To be honest, manual judging will inevitably result in some sort of bias (although bias is not necessarily a bad thing depending on user intent and practices, i.e is he frugal, brand based, quality etc). But looking at pgvector that I implemented and pinecone, there is only ONE difference between them and that is query 2 result 5 where pinecone determined the best to be athletic leggings and pgvector decided the best to be chelsea boots. Which is better? I think it would differ based on who you ask. So in terms of relevnecy I would say both are pretty spot on based on strictly what the query asked. [for harshness, ill manually evaluate things that are semi relvent as nill, for example for wireless earbuds, the result laptop sleeve and bluetooth speaker are maybe relevent based on tech, but for this purposes ill treat them as not] [also both versions take into price as the source of truth, in actuality we would a more nuaunced approach, maybe more 70-30 split between price and and relevent info]

| Query                                | Pinecone P@5 | pgvector P@5 |
|--------------------------------------|--------------|---------------|
| linen summer dress under $300        | 5/5          | 5/5           |
| running shoes under $120             | 3/5          | 4/5           |
| wireless earbuds under $80           | 3/5          | 3/5           |
| coffee maker under $100              | 2/5          | 2/5           |
| gaming mouse                         | 5/5          | 5/5           |
| 4k tv under $600                     | 5/5          | 5/5           |
| winter jacket                        | 5/5          | 5/5           |
| yoga mat under $30                   | ☐/5    NA      | ☐/5    NA        |
| portable bluetooth speaker           | 5/5          | 5/5           |
| office chair ergonomic under $200    | 2/5          | 2/5           |


---

### Reflections and Improvements

- Retrieval quality:
  - Tune IVFFlat parameters per dataset size (increase `PGVECTOR_LISTS`, `PGVECTOR_PROBES`);
  - Push hard filters (price/category) into SQL where possible to avoid post‑filter loss.

- reranking:
  - Calibrate dense vs BM25 weight, maybe try adaptive weighting by query length.
  - Add a cross‑encoder reranker.

- Embeddings:
  - Try domain-tuned or larger models
  - Normalize and truncate long descriptions
  - add synonyms/keyword expansion for sparse signals.

- Data and filtering:
  - Enforce price/type validation during ingest
  - Store price as a real column alongside JSONB.

- Evaluation:
  - maybe add nDCG@5 and Recall@10.

### Pinecone

- **Query: linen summer dress under $300**
  1. [270] Linen Summer Dress $293.20
  2. [18] Linen Summer Dress $92.44
  3. [44] Linen Summer Dress $273.20
  4. [198] Linen Summer Dress $260.78
  5. [158] Linen Summer Dress $172.42

- **Query: running shoes under $120**
  1. [357] Classic Leather Sneakers $44.05
  2. [189] Classic Leather Sneakers $69.41
  3. [55] Classic Leather Sneakers $57.83
  4. [50] Athletic Leggings $109.21
  5. [153] Athletic Leggings $60.46

- **Query: wireless earbuds under $80**
  1. [266] Wireless Earbuds $33.80
  2. [147] Noise-Cancelling Headphones $65.14
  3. [159] Noise-Cancelling Headphones $31.25
  4. [340] Laptop Sleeve $43.53
  5. [436] Bluetooth Speaker $64.24

- **Query: coffee maker under $100**
  1. [313] Espresso Machine $89.25
  2. [57] Electric Kettle $88.08
  3. [404] Storage Basket $48.39
  4. [426] Storage Basket $63.49
  5. [152] Smart Home Hub $95.68

- **Query: gaming mouse**
  1. [494] Gaming Mouse $159.63
  2. [222] Gaming Mouse $351.17
  3. [28] Gaming Mouse $641.81
  4. [371] Gaming Mouse $126.30
  5. [229] Gaming Mouse $35.69

- **Query: 4k tv under $600**
  1. [240] 4K Webcam $441.68
  2. [60] 4K Webcam $596.65
  3. [260] 4K Webcam $67.65
  4. [218] 4K Webcam $304.85
  5. [279] 4K Webcam $357.73

- **Query: winter jacket**
  1. [381] Puffer Jacket $73.56
  2. [213] Puffer Jacket $107.15
  3. [455] Puffer Jacket $152.56
  4. [481] Puffer Jacket $81.08
  5. [12] Puffer Jacket $89.87

- **Query: yoga mat under $30**
  - (no results)

- **Query: portable bluetooth speaker**
  1. [475] Bluetooth Speaker $242.72
  2. [157] Bluetooth Speaker $427.57
  3. [69] Bluetooth Speaker $466.81
  4. [148] Bluetooth Speaker $509.84
  5. [95] Bluetooth Speaker $511.55

- **Query: office chair ergonomic under $200**
  1. [301] Dining Chair $123.80
  2. [379] Dining Chair $155.49
  3. [434] Portable Projector $119.96
  4. [350] Mechanical Keyboard $184.03
  5. [52] Foldable Phone Stand $49.98

Latency (ms): avg=76.84, p95=149.66

---

### pgvector

- **Query: linen summer dress under $300**
  1. [270] Linen Summer Dress $293.20
  2. [18] Linen Summer Dress $92.44
  3. [44] Linen Summer Dress $273.20
  4. [198] Linen Summer Dress $260.78
  5. [158] Linen Summer Dress $172.42

- **Query: running shoes under $120**
  1. [357] Classic Leather Sneakers $44.05
  2. [189] Classic Leather Sneakers $69.41
  3. [55] Classic Leather Sneakers $57.83
  4. [50] Athletic Leggings $109.21
  5. [30] Chelsea Boots $40.46

- **Query: wireless earbuds under $80**
  1. [266] Wireless Earbuds $33.80
  2. [147] Noise-Cancelling Headphones $65.14
  3. [159] Noise-Cancelling Headphones $31.25
  4. [340] Laptop Sleeve $43.53
  5. [436] Bluetooth Speaker $64.24

- **Query: coffee maker under $100**
  1. [313] Espresso Machine $89.25
  2. [57] Electric Kettle $88.08
  3. [404] Storage Basket $48.39
  4. [426] Storage Basket $63.49
  5. [152] Smart Home Hub $95.68

- **Query: gaming mouse**
  1. [494] Gaming Mouse $159.63
  2. [222] Gaming Mouse $351.17
  3. [28] Gaming Mouse $641.81
  4. [371] Gaming Mouse $126.30
  5. [229] Gaming Mouse $35.69

- **Query: 4k tv under $600**
  1. [240] 4K Webcam $441.68
  2. [60] 4K Webcam $596.65
  3. [260] 4K Webcam $67.65
  4. [218] 4K Webcam $304.85
  5. [279] 4K Webcam $357.73

- **Query: winter jacket**
  1. [381] Puffer Jacket $73.56
  2. [213] Puffer Jacket $107.15
  3. [455] Puffer Jacket $152.56
  4. [481] Puffer Jacket $81.08
  5. [12] Puffer Jacket $89.87

- **Query: yoga mat under $30**
  - (no results)

- **Query: portable bluetooth speaker**
  1. [475] Bluetooth Speaker $242.72
  2. [157] Bluetooth Speaker $427.57
  3. [69] Bluetooth Speaker $466.81
  4. [148] Bluetooth Speaker $509.84
  5. [95] Bluetooth Speaker $511.55

- **Query: office chair ergonomic under $200**
  1. [301] Dining Chair $123.80
  2. [379] Dining Chair $155.49
  3. [434] Portable Projector $119.96
  4. [350] Mechanical Keyboard $184.03
  5. [52] Foldable Phone Stand $49.98

Latency (ms): avg=15.98, p95=46.37

