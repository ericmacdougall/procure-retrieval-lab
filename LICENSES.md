# Data, models and dependencies

UK Contracts Finder public notices: [Contracts Finder API documentation](https://www.contractsfinder.service.gov.uk/apidocumentation/home). The recorded feed packages identify the [Open Government Licence version 3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Attribution: contains public sector information licensed under the Open Government Licence v3.0. Original buyer/supplier names are public records and are not facts about the course author or any client.

Dense model: [BAAI/bge-small-en-v1.5 model card](https://huggingface.co/BAAI/bge-small-en-v1.5), MIT as specified in the publisher's model metadata. Exact revision is pinned in `src/dense.py`.

Cross-encoder: [cross-encoder/ms-marco-MiniLM-L6-v2 model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2), Apache 2.0 as specified by the publisher. Exact revision is pinned in `src/rerank.py`.

Python dependencies remain under their respective upstream licences. Their exact installed versions are recorded in `requirements.lock.txt`; dependencies and model weights are not relicensed under this project's MIT code licence.
