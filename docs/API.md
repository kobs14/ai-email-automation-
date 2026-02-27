# API Reference

The Flask REST API is available at `http://localhost:5000`. All endpoints except `/api/health` and `/api/auth/login` require a JWT Bearer token.

## Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login and receive JWT tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Logout (blacklist token) |
| GET | `/api/auth/me` | Get current user info |

## Emails
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/emails` | Paginated email list with search/filter |
| GET | `/api/emails/:id` | Email detail with entities and response |
| GET | `/api/emails/:id/entities` | Extracted entities for an email |

## Responses
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/responses` | Paginated response list |
| GET | `/api/responses/pending` | Pending draft responses |
| GET | `/api/responses/failed` | Failed responses |
| GET | `/api/responses/:id` | Response detail with email context |
| PUT | `/api/responses/:id/content` | Edit draft content (admin/operator) |
| POST | `/api/responses/:id/approve` | Approve a draft (admin/operator) |
| POST | `/api/responses/:id/reject` | Reject a draft (admin/operator) |
| POST | `/api/responses/:id/retry` | Retry a failed response (admin/operator) |

## Calendar
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/calendar` | List calendar events |
| GET | `/api/calendar/conflicts` | Check for scheduling conflicts |

## Configuration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Get all configuration |
| GET | `/api/config/:key` | Get specific config value |
| PUT | `/api/config/:key` | Update config value (admin only) |

## Statistics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Dashboard metrics and aggregations |

## Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Database and Redis connectivity check |
