# Claude Code Development Guidelines

## Project Context
This is a Python-based microservices application using Flask, PostgreSQL, Redis, and Docker. The architecture follows a distributed pattern with multiple services communicating via Redis Pub/Sub.

## Core Development Principles

### Code Quality Standards
- Use raw SQL queries with psycopg2 for database operations (avoid SQLAlchemy ORM)
- Follow PEP 8 style guidelines strictly
- Write comprehensive docstrings for all functions and classes
- Include type hints for all function parameters and return values
- Keep functions focused and under 50 lines when possible

### Architecture Patterns
- Microservices communicate via Redis Pub/Sub, not direct HTTP calls
- Each service runs in its own Docker container
- Use Flask for API endpoints, not FastAPI
- Implement proper error handling and logging in all services
- Use environment variables for configuration, never hardcode credentials

### Database Practices
- Use PostgreSQL with proper connection pooling
- Write migrations as raw SQL files in `migrations/` directory
- Always use parameterized queries to prevent SQL injection
- Include database indexes for frequently queried columns
- Close database connections properly in all code paths

### Docker and Deployment
- Each service has its own Dockerfile
- Use docker-compose for local development
- Include health checks in Docker containers
- Mount code as volumes during development for hot-reloading
- Use named volumes for persistent data (postgres, redis)

### Testing Requirements
- Write unit tests for all business logic
- Include integration tests for service-to-service communication
- Use pytest as the testing framework
- Mock external dependencies in unit tests
- Achieve minimum 80% code coverage

### Redis Usage
- Use Redis for caching with appropriate TTLs
- Implement Redis Pub/Sub for inter-service messaging
- Include retry logic for Redis connection failures
- Set reasonable timeouts for Redis operations
- Document all Redis keys and their purpose

### API Design
- Use RESTful conventions for all endpoints
- Return proper HTTP status codes
- Include request validation for all endpoints
- Document APIs with clear docstrings or OpenAPI specs
- Implement rate limiting where appropriate

### Error Handling
- Never use bare `except:` clauses
- Log all errors with appropriate context
- Return user-friendly error messages in APIs
- Use custom exception classes for domain-specific errors
- Include error tracking/monitoring integration points

### Logging Practices
- Use structured logging with JSON format
- Include correlation IDs for request tracing
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Never log sensitive data (passwords, tokens, PII)
- Configure log rotation and retention

### Security Requirements
- Validate and sanitize all user inputs
- Use environment variables for secrets
- Implement authentication for all API endpoints
- Use HTTPS in production environments
- Follow OWASP security best practices

## Project-Specific Guidelines

### Email Processing Service
- Parse emails with proper error handling for malformed content
- Extract key information: sender, subject, body, attachments
- Clean and normalize text before classification
- Handle different email formats (plain text, HTML, multipart)

### Classification Service
- Use Claude API for email classification
- Implement proper rate limiting for API calls
- Cache classification results when appropriate
- Handle API failures gracefully with retries
- Log all API requests for debugging

### Quote Generation Service
- Generate quotes based on service type and requirements
- Use templates with proper variable substitution
- Validate all generated quotes before sending
- Include proper formatting for currency and dates
- Track quote history in database

### Response Automation
- Never send automated responses without human review flag
- Include unsubscribe links in all automated emails
- Log all sent emails for audit trail
- Implement sending rate limits to avoid spam flags
- Use proper email headers (Reply-To, From, etc.)

### Telegram Bot Interface
- Implement proper command handling
- Provide clear error messages to users
- Include rate limiting per user
- Log all user interactions
- Handle bot API failures gracefully

## Tools and Libraries

### Preferred Libraries
- Flask for web framework
- psycopg2 for PostgreSQL
- redis-py for Redis operations
- python-dotenv for environment management
- pytest for testing
- requests for HTTP calls
- python-telegram-bot for Telegram integration

### Avoid Using
- SQLAlchemy (use raw SQL instead)
- FastAPI (use Flask instead)
- Complex ORMs
- Synchronous blocking in async contexts

## Common Mistakes to Avoid

### Database
- ❌ Don't forget to close database connections
- ❌ Don't use string concatenation for SQL queries
- ❌ Don't commit transactions in the middle of operations
- ❌ Don't ignore database connection errors

### Docker
- ❌ Don't run containers as root user
- ❌ Don't expose unnecessary ports
- ❌ Don't use latest tag for production images
- ❌ Don't forget to clean up unused containers and images

### Redis
- ❌ Don't set infinite TTLs for cache entries
- ❌ Don't forget to handle connection failures
- ❌ Don't use blocking operations in main thread
- ❌ Don't store large objects in Redis without compression

### API Development
- ❌ Don't return stack traces in API responses
- ❌ Don't trust user input without validation
- ❌ Don't use GET requests for state-changing operations
- ❌ Don't forget CORS configuration for frontend

### Python Code
- ❌ Don't use mutable default arguments
- ❌ Don't catch exceptions without logging them
- ❌ Don't use global variables for state
- ❌ Don't forget to close file handles

## Development Workflow

### Starting New Features
1. Create feature branch from main
2. Write tests first (TDD approach)
3. Implement feature with proper error handling
4. Update documentation
5. Run full test suite locally
6. Create PR with clear description

### Code Review Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No hardcoded credentials
- [ ] Error handling implemented
- [ ] Logging added where appropriate
- [ ] Database migrations included if needed
- [ ] No security vulnerabilities introduced

### Deployment Process
- Build Docker images with version tags
- Run integration tests in staging environment
- Check logs for any errors
- Monitor service health after deployment
- Be ready to rollback if issues occur

## Performance Considerations
- Use connection pooling for database and Redis
- Implement caching for frequently accessed data
- Use async operations where appropriate
- Monitor and optimize slow database queries
- Profile code for bottlenecks before optimization

## Monitoring and Debugging
- Include health check endpoints for all services
- Log all errors with full context
- Use correlation IDs to trace requests across services
- Monitor Redis and PostgreSQL performance metrics
- Set up alerts for critical errors

## Documentation
- Keep README.md up to date with setup instructions
- Document all environment variables
- Include architecture diagrams
- Maintain API documentation
- Document deployment procedures

---

*This file should be updated whenever new patterns or anti-patterns are discovered during development.*
