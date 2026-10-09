# Licenses and datasets

Application code in this repository is Apache-2.0. See `LICENSE`.

The local object-storage image is `pgsty/silo`, pinned by digest in `docker-compose.yml`. It is a separate server process. Do not treat its license as Apache-2.0.

## Datasets

| Name | Source | License found | What this repo does |
| --- | --- | --- | --- |
| MFAD | https://github.com/EMRGSZU/MFAD | No license file | Filename and modality inspection only. Not RGB competition footage. Not redistributed. |
| Fencing Footwork Dataset | https://galaxy.agh.edu.pl/~fmal/ffd/ | Unspecified | Optional local MATLAB and depth inspection. Not redistributed. |
| FIE fencing dataset | https://github.com/amichaelsen/fie-fencing-dataset | GPL-3.0 | Original CSV reader. Upstream code is not copied. A CC0 Kaggle export does not relicense the generator. |
| fencing-AI | https://github.com/sholtodouglas/fencing-AI | No license | Method notes only. The scoreboard detector here is original and does not decide referee calls. |
| FencingVision | https://github.com/Ph1n-Pham/fencing-vision | No license | No code reused. |
| FIE and FFE rules | https://fie.org/documents/rules and https://www.ffescrime.fr/je-suis-en-club/competiteurs/reglements/ | Official documents | Short original labels and source URLs. Rule text is not stored. |
| Athlete uploads | This application | Private | Stored for the organization. Training use requires an explicit consent record. |

`datasets doctor` is the operational check. A missing dataset is expected until an operator adds a local manifest. Do not download these archives from the application.

`FI-synthetic-epee` is original data written in this repository and licensed Apache-2.0. It exists so import and evaluation code can run without those external archives. It is not a copy of them and it is not competition footage.

The pose file `pose_landmarker_lite.task` is Google's MediaPipe Pose Landmarker, Apache-2.0. It estimates body landmarks. It does not classify fencing actions.

Object storage does not require the MinIO image. Any S3 API works. Local Compose uses the pinned Silo image because anonymous pulls of `minio/minio` failed. Set `S3_ENDPOINT_URL` to Garage, Cloudflare R2, AWS, or another S3 service when you do not want to run Silo.
