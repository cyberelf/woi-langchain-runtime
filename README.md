# LangChain Agent Runtime

A LangChain/LangGraph-based agent runtime service that implements the AI Platform Agent Runtime API specification. This service provides agent lifecycle management, OpenAI-compatible execution, and dynamic schema synchronization.

## Features

- **Agent Management**: Create, update, and delete agents with different types (conversation, task, custom)
- **LangGraph Integration**: Uses LangGraph for complex agent workflows and state management
- **OpenAI Compatibility**: Provides OpenAI-compatible chat completions API
- **Streaming Support**: Real-time streaming responses for better user experience
- **Schema Synchronization**: Dynamic schema discovery and validation
- **Health Monitoring**: Comprehensive health checks and metrics
- **LLM Proxy Integration**: Supports LLM Proxy service with fallback to direct OpenAI
- **Type Safety**: Full type annotations and Pydantic validation

## Architecture

The runtime is built using:

- **FastAPI**: Modern, fast web framework for building APIs
- **LangChain**: Framework for developing applications with language models
- **LangGraph**: Library for building stateful, multi-actor applications with LLMs
- **Pydantic**: Data validation using Python type annotations
- **Structured Logging**: JSON-structured logging for better observability

## Agent Types

### 1. Conversation Agent (智能客服助手)
- Basic conversational AI with configurable history length
- Suitable for customer service and general chat applications
- Template ID: `customer-service-bot`

### 2. Task Agent (任务型智能体)
- Step-by-step task execution with validation
- Configurable retry logic and parallel execution
- Template ID: `task-execution-bot`

### 3. Custom Agent (自定义智能体)
- User-defined code execution in sandboxed environment
- Support for Python, JavaScript, and TypeScript
- Template ID: `custom-code-bot`

## Installation

### Using Poetry (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd langchain-runtime

# Install dependencies
poetry install

# Copy environment configuration
cp env.example .env
# Edit .env with your configuration

# Run the service
poetry run python -m runtime.main
```

### Using Docker

```bash
# Build the image
docker build -t langchain-runtime .

# Run the container
docker run -p 8000:8000 --env-file .env langchain-runtime
```

## Configuration

The service is configured using environment variables. Copy `env.example` to `.env` and configure:

### Required Configuration

```bash
# Authentication token for runtime API
RUNTIME_TOKEN=your-secure-token-here

# LLM Proxy service URL
LLM_PROXY_URL=http://localhost:8001
```

### Optional Configuration

```bash
# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=false

# LLM Proxy authentication
LLM_PROXY_TOKEN=your-llm-proxy-token

# OpenAI fallback (if LLM Proxy unavailable)
OPENAI_API_KEY=your-openai-api-key

# Runtime limits
MAX_CONCURRENT_AGENTS=100
MAX_MESSAGE_LENGTH=32000
MAX_CONVERSATION_HISTORY=100

# Timeouts (seconds)
AGENT_EXECUTION_TIMEOUT=300
LLM_REQUEST_TIMEOUT=60

# Logging
LOG_LEVEL=INFO
```

## API Endpoints

### Agent Management

- `POST /v1/agents` - Create a new agent
- `PUT /v1/agents/{agent_id}` - Update an existing agent
- `DELETE /v1/agents/{agent_id}` - Delete an agent

### Schema Discovery

- `GET /v1/schema` - Get runtime schema and supported templates

### Agent Execution

- `POST /v1/chat/completions` - Execute agent (OpenAI-compatible)

### Health & Monitoring

- `GET /v1/health` - Comprehensive health check
- `GET /ping` - Simple ping endpoint

## Usage Examples

### Creating a Conversation Agent

```bash
curl -X POST "http://localhost:8000/v1/agents" \
  -H "X-Runtime-Token: your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "customer-service-1",
    "name": "Customer Service Bot",
    "description": "Handles customer inquiries",
    "type": "conversation",
    "template_id": "customer-service-bot",
    "template_version_id": "1.0.0",
    "template_config": {
      "conversation": {
        "continuous": true,
        "historyLength": 10
      }
    },
    "system_prompt": "You are a helpful customer service agent.",
    "llm_config_id": "gpt-3.5-turbo"
  }'
```

### Executing an Agent

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "X-Runtime-Token: your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "customer-service-1",
    "messages": [
      {
        "role": "user",
        "content": "Hello, I need help with my order"
      }
    ],
    "stream": false
  }'
```

### Streaming Response

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "X-Runtime-Token: your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "customer-service-1",
    "messages": [
      {
        "role": "user",
        "content": "Tell me about your services"
      }
    ],
    "stream": true
  }'
```

## Development

### Running in Development Mode

```bash
# Install development dependencies
poetry install

# Run with auto-reload
DEBUG=true RELOAD=true poetry run python -m runtime.main
```

### Code Quality

```bash
# Format code
poetry run black runtime/

# Sort imports
poetry run isort runtime/

# Type checking
poetry run mypy runtime/

# Linting
poetry run flake8 runtime/
```

### Testing

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=runtime
```

## Monitoring

The service provides comprehensive monitoring through:

### Health Checks

- **LLM Proxy**: Connection and response time
- **Database**: Connection status (if applicable)
- **Agent Templates**: Template loading status

### Metrics

- Active agents count
- Total executions
- Average response time
- Error rate

### Logging

Structured JSON logging includes:

- Request/response logging
- Error tracking with stack traces
- Performance metrics
- Agent execution steps

## Security

- **Authentication**: Runtime token-based authentication
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: Configurable limits on concurrent agents
- **Sandboxing**: Secure execution environment for custom agents
- **HTTPS**: TLS encryption for all communications

## Deployment

### Production Deployment

1. **Environment Setup**:
   ```bash
   # Production environment variables
   DEBUG=false
   LOG_LEVEL=INFO
   RUNTIME_TOKEN=<secure-random-token>
   ```

2. **Container Deployment**:
   ```bash
   docker run -d \
     --name langchain-runtime \
     -p 8000:8000 \
     --env-file .env \
     --restart unless-stopped \
     langchain-runtime
   ```

3. **Health Monitoring**:
   - Configure load balancer health checks to `/ping`
   - Set up monitoring alerts for `/v1/health` endpoint
   - Monitor logs for error patterns

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langchain-runtime
spec:
  replicas: 3
  selector:
    matchLabels:
      app: langchain-runtime
  template:
    metadata:
      labels:
        app: langchain-runtime
    spec:
      containers:
      - name: runtime
        image: langchain-runtime:latest
        ports:
        - containerPort: 8000
        env:
        - name: RUNTIME_TOKEN
          valueFrom:
            secretKeyRef:
              name: runtime-secrets
              key: token
        livenessProbe:
          httpGet:
            path: /ping
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Troubleshooting

### Common Issues

1. **LLM Proxy Connection Failed**:
   - Check `LLM_PROXY_URL` configuration
   - Verify network connectivity
   - Check LLM Proxy service status

2. **Agent Creation Failed**:
   - Validate template configuration
   - Check required fields for agent type
   - Review validation error messages

3. **High Response Times**:
   - Monitor LLM Proxy performance
   - Check agent execution steps
   - Review conversation history limits

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true LOG_LEVEL=DEBUG poetry run python -m runtime.main
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Check the [API documentation](http://localhost:8000/docs) when running in debug mode
- Review the health check endpoint for system status
- Check structured logs for detailed error information
