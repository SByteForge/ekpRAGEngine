# Enterprise Knowledge Platform (EKP)

## Overview
The Enterprise Knowledge Platform (EKP) is a multi-tenant Retrieval-Augmented Generation (RAG) platform designed for querying internal organizational documents using natural language. It emphasizes governance, citation, and the measurement of retrieval and generation quality.

## Project Structure
The project is organized into several packages, each serving a distinct purpose:

- **app/**
  - **api/**: Contains FastAPI routes for handling requests.
  - **core/**: Shared configurations and utilities.
  - **eval/**: Metrics and evaluation logic for retrieval and generation.
  - **generation/**: Logic for generating responses based on user queries.
  - **ingestion/**: Handles document parsing, chunking, embedding, and indexing.
  - **retrieval/**: Implements search and retrieval methods.
  - **tenancy/**: Manages multi-tenancy features.

## Getting Started

### Prerequisites
- Python 3.x
- Docker and Docker Compose

### Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd ekp-project
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up the environment:
   - Ensure that your environment variables are configured as needed.

### Running the Application
To run the application using Docker Compose, execute:
```
docker-compose up
```

### Testing
To run the tests, use:
```
pytest tests/
```

## Evaluation
The project includes an evaluation harness that measures retrieval and generation performance. Ensure to populate the evaluation results section as you run the harness.

## Future Development
The roadmap includes plans for transitioning to a microservices architecture, enhancing observability, and implementing full multi-tenancy and security features.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for discussion.

## License
This project is licensed under the MIT License. See the LICENSE file for details.