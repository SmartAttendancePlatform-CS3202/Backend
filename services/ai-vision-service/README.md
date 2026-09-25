# ai-vision-service

High-performance, lightweight vector matching microservice for face verification —
PID 12 / Group 24's Smart Attendance and Classroom Access Platform.

## Architecture

- **Edge-First Embedding**: Mobile clients execute on-device liveness verification and extract 512-dimensional embeddings via FaceNet 512 (`react-native-fast-tflite`).
- **No Server-Side Image Generation**: The backend performs zero neural network inference on raw images, eliminating heavy ML frameworks (DeepFace, OpenCV, TensorFlow).
- **In-Memory Cosine Similarity**: Normalized dot products are computed in Python via NumPy with sub-millisecond latency.
- **Data Ownership**: Exclusively owns `face_profiles` (`vector(512)` pgvector embeddings).
- **Security**: Internal only. Endpoints require the `X-Internal-Key` header verified by shared RBAC.

## Endpoints

- `GET /health` — Health check endpoint
- `POST /internal/verify` — Internal 1:1 vector verification against active student profile
- `POST /internal/register` — Internal registration of student's 512D reference embedding

## Asynchronous Worker (RabbitMQ)

- Consumes `FaceVerificationTask` from `face_verification_queue` (containing 512D `face_embedding`).
- Performs 1:1 matching against stored student profile.
- Publishes `FaceVerificationResult` to `face_verification_results` queue for `attendance-service` to record.
