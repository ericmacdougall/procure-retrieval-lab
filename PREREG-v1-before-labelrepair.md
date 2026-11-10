# Pre-registration

Fixed before any tuning or sealed evaluation.

```json
{
  "version": 1,
  "timestamp": "2026-11-10T06:22:04.058077+00:00",
  "seed": 20261110,
  "total_n": 414,
  "answerable_n": 354,
  "no_answer_n": 60,
  "primary": "nDCG@10 on answerable questions",
  "bootstrap": 10000,
  "baseline": "baseline-bm25",
  "superiority_rule": "paired 95% bootstrap CI lower bound > 0",
  "slice_regression_margin": 0.05,
  "scope": "Document-disjoint generated queries over a fixed known procurement corpus. Buyer and contract families overlap across partitions; no new-buyer or human-user generalization claim.",
  "candidate_budget": 22,
  "configs": [
    [
      "baseline-bm25",
      {
        "system": "bm25"
      }
    ],
    [
      "baseline-dense",
      {
        "system": "dense"
      }
    ],
    [
      "baseline-hybrid",
      {
        "system": "hybrid"
      }
    ],
    [
      "baseline-rerank",
      {
        "system": "rerank",
        "rerank_n": 20
      }
    ],
    [
      "bm25-k0.6-b0.75",
      {
        "system": "bm25",
        "k1": 0.6,
        "b": 0.75
      }
    ],
    [
      "bm25-k2.0-b0.75",
      {
        "system": "bm25",
        "k1": 2.0,
        "b": 0.75
      }
    ],
    [
      "bm25-k1.2-b0.0",
      {
        "system": "bm25",
        "k1": 1.2,
        "b": 0.0
      }
    ],
    [
      "bm25-k1.2-b0.5",
      {
        "system": "bm25",
        "k1": 1.2,
        "b": 0.5
      }
    ],
    [
      "bm25-k1.2-b1.0",
      {
        "system": "bm25",
        "k1": 1.2,
        "b": 1.0
      }
    ],
    [
      "chunk-plain-64",
      {
        "system": "bm25",
        "chunk": {
          "mode": "plain",
          "size": 64,
          "overlap": 16,
          "prefix_title": true
        }
      }
    ],
    [
      "chunk-plain-256",
      {
        "system": "bm25",
        "chunk": {
          "mode": "plain",
          "size": 256,
          "overlap": 64,
          "prefix_title": true
        }
      }
    ],
    [
      "chunk-field-128",
      {
        "system": "bm25",
        "chunk": {
          "mode": "field",
          "size": 128,
          "overlap": 32,
          "prefix_title": true
        }
      }
    ],
    [
      "rrf-10",
      {
        "system": "hybrid",
        "rrf_k": 10
      }
    ],
    [
      "rrf-120",
      {
        "system": "hybrid",
        "rrf_k": 120
      }
    ],
    [
      "weight-0.25",
      {
        "system": "hybrid",
        "fusion": "weighted",
        "weight": 0.25
      }
    ],
    [
      "weight-0.5",
      {
        "system": "hybrid",
        "fusion": "weighted",
        "weight": 0.5
      }
    ],
    [
      "weight-0.75",
      {
        "system": "hybrid",
        "fusion": "weighted",
        "weight": 0.75
      }
    ],
    [
      "rerank-5",
      {
        "system": "rerank",
        "rerank_n": 5
      }
    ],
    [
      "rerank-10",
      {
        "system": "rerank",
        "rerank_n": 10
      }
    ],
    [
      "rewrite-bm25",
      {
        "system": "bm25",
        "rewrite": true
      }
    ],
    [
      "rewrite-hybrid",
      {
        "system": "hybrid",
        "rewrite": true
      }
    ],
    [
      "depth-100",
      {
        "system": "hybrid",
        "chunk_depth": 100
      }
    ]
  ],
  "additional_arm": "Rule-based structured-tool routing over the same registry, compared separately for ax02, never an LLM planner claim",
  "no_answer_policy": "Threshold chosen on development top-score balanced answerability accuracy; frozen and evaluated separately on no-answer cases",
  "small_benchmark_demo": "Choose best declared configuration on twelve stratified answerable test-lock questions (two per slice), compare on remaining test-lock questions. This intentional misuse is separate from dev-only final selection.",
  "question_hashes": {
    "questions/dev.jsonl": "cb209218ed8ab727fbc9ddd5a096973aa427009f8b814b338e31b4e804e741cf",
    "questions/train.jsonl": "d580a3ae05df66fd48820118905065dde3911594af2bd56f2f6097af30e37715",
    "questions/dev.template.jsonl": "294605697ef3648734b59914c63c6624c2bd9f7c99a6873ee187c8d97ca3f956",
    "questions/testlock.template.jsonl": "481c34bfc367a12e8ee161078f7f47f23d27092f4772163da4a43efca040d3cb",
    "questions/testlock.jsonl": "e77bc1c4cb6b0eb2a0c93aa1497f2a79c571c719ae8404c747ba86748a8ffb33",
    "questions/train.template.jsonl": "6aa61f65fd31dabce8b3763d45ff30836346ac81f1e1b24af38f9fd0b1924049"
  },
  "heldout_hash": "a564d1a588c008c557fb3166f4bd8711170b05085690380e43cc1fe0d6b75026",
  "filtering_limitation": "Ambiguous repeated-prefix questions removed before tuning, making the filtered task easier than the raw query mix; known-source generated-query benchmark only.",
  "dropped_questions": [
    {
      "id": "Qb8fecbea0e",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 86
    },
    {
      "id": "Qb273071169",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Q7199b14219",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Q6262cbd70d",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Q1a7e81d9c6",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Qa0ee32d46c",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 3
    },
    {
      "id": "Q71e2b64fec",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 2
    },
    {
      "id": "Q99eb791b8c",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 2
    },
    {
      "id": "Q210a541f43",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 86
    },
    {
      "id": "Qb9d44ed9b1",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 2
    },
    {
      "id": "Qf2ba9575af",
      "split": "train",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 28
    },
    {
      "id": "Qf3199f08b2",
      "split": "dev",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 8
    },
    {
      "id": "Q7a093bacb6",
      "split": "dev",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 3
    },
    {
      "id": "Q242613d897",
      "split": "dev",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 8
    },
    {
      "id": "Q4c30eef6cd",
      "split": "dev",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 86
    },
    {
      "id": "Q1d6351995a",
      "split": "testlock",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 3
    },
    {
      "id": "Qd2d50845b9",
      "split": "testlock",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Q8e732cb29b",
      "split": "testlock",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 5
    },
    {
      "id": "Q27758ebe04",
      "split": "testlock",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 8
    },
    {
      "id": "Qb8a1482a6e",
      "split": "testlock",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 3
    },
    {
      "id": "Q708a8a46c2",
      "split": "testlock",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 2
    },
    {
      "id": "Q12bf7d23fd",
      "split": "testlock",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 4
    },
    {
      "id": "Qa2112f4e60",
      "split": "testlock",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Q8581f07a23",
      "split": "heldout",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Qeacbb2c644",
      "split": "heldout",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Q84798ab143",
      "split": "heldout",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Q4a193302f9",
      "split": "heldout",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Q9880b6fea2",
      "split": "heldout",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 20
    },
    {
      "id": "Qddfc595bd0",
      "split": "heldout",
      "reason": "ambiguous_24_word_description_prefix",
      "matching_documents": 472
    },
    {
      "id": "Q08eeec8363",
      "split": "train",
      "reason": "failed_semantic_rewording_validation_after_one_targeted_repair"
    },
    {
      "id": "Q426c6ff464",
      "split": "dev",
      "reason": "failed_semantic_rewording_validation_after_one_targeted_repair"
    },
    {
      "id": "Qe3cc705318",
      "split": "dev",
      "reason": "failed_semantic_rewording_validation_after_one_targeted_repair"
    },
    {
      "id": "Q152054d8af",
      "split": "dev",
      "reason": "failed_semantic_rewording_validation_after_one_targeted_repair"
    },
    {
      "id": "Qa5f66711c5",
      "split": "testlock",
      "reason": "failed_semantic_rewording_validation_after_one_targeted_repair"
    }
  ],
  "corpus_hash": "093de51a75ebb072f825904b1297a86b1b0949db28c62ce1377ae7842e12f1cd",
  "selection": "Highest dev nDCG@10 among declared configurations; ties prefer earlier candidate. Heldout outcome never changes selection.",
  "nonpositive_result": "A failure to establish superiority is a valid experiment result, never a reason to retune against heldout."
}
```
