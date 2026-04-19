# API Quick Reference

## Base URL
```
http://localhost:8000/api
```

## Endpoints At A Glance

### User Management
```
POST   /users                    Create user
GET    /users/{id}              Get user
PATCH  /users/{id}              Update user
```

### Resume Operations
```
POST   /users/{id}/resume       Upload resume
PUT    /users/{id}/resume       Update resume
GET    /users/{id}/resume       Get resume text
```

### Job Analysis
```
POST   /resume/analyze          Analyze resume (mock)
POST   /generate/answer         Generate answer (mock)
POST   /users/{id}/score        Score resume (Agent)
POST   /users/{id}/answer       Generate answer (Agent)
```

---

## Request/Response Examples

### 1️⃣ Create User
```bash
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "years_of_experience": 5
  }'
```

**Response:** `200 OK`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "years_of_experience": 5,
  "has_resume": false,
  "created_at": "2024-04-19T10:30:00Z",
  "updated_at": "2024-04-19T10:30:00Z"
}
```

---

### 2️⃣ Get User
```bash
curl http://localhost:8000/api/users/{user_id}
```

**Response:** `200 OK` (User object)

---

### 3️⃣ Update User
```bash
curl -X PATCH http://localhost:8000/api/users/{user_id} \
  -H "Content-Type: application/json" \
  -d '{
    "desired_job_title": "Senior Engineer"
  }'
```

**Response:** `200 OK` (Updated user object)

---

### 4️⃣ Upload Resume
```bash
curl -X POST http://localhost:8000/api/users/{user_id}/resume \
  -F "file=@/path/to/resume.pdf"
```

**Response:** `200 OK`
```json
{
  "filename": "resume.pdf",
  "uploaded_at": "2024-04-19T10:35:00Z",
  "mimetype": "application/pdf"
}
```

---

### 5️⃣ Analyze Resume
```bash
curl -X POST http://localhost:8000/api/resume/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "job_url": "https://linkedin.com/jobs/view/123456/"
  }'
```

**Response:** `200 OK`
```json
{
  "match_percentage": 78.5,
  "key_matches": [
    "Python experience",
    "FastAPI knowledge",
    "API design"
  ],
  "gaps": [
    "Kubernetes experience",
    "AWS knowledge"
  ],
  "recommendations": [
    "Learn Docker and Kubernetes",
    "Get AWS certification"
  ]
}
```

---

### 6️⃣ Generate Answer
```bash
curl -X POST http://localhost:8000/api/generate/answer \
  -H "Content-Type: application/json" \
  -d '{
    "job_url": "https://linkedin.com/jobs/view/123456/",
    "user_question": "Tell us about your experience with microservices?"
  }'
```

**Response:** `200 OK`
```json
{
  "answer": "In my previous role at TechCorp, I led a team of 5 engineers...",
  "relevance_score": 92.0
}
```

---

## HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| `200` | Success | GET, POST returns data |
| `201` | Created | Resource created |
| `400` | Bad Request | Invalid JSON format |
| `404` | Not Found | User ID doesn't exist |
| `422` | Validation Error | Invalid file type |
| `502` | Bad Gateway | Agent service error |
| `503` | Unavailable | Agent service down |

---

## Data Validation Rules

### User Fields
- **email**: Valid email format (required)
- **first_name**: 1-100 characters (required)
- **last_name**: 1-100 characters (required)
- **years_of_experience**: 0 or greater (optional)

### Resume Files
- **Allowed Types**: PDF, DOCX, DOC, TXT
- **Max Size**: No limit (remove in production)

### Analysis Requests
- **job_url**: Valid URL format (required)
- **user_question**: Non-empty string (required)

---

## Error Responses

All errors return JSON with `detail` field:

```json
{
  "detail": "User with ID xxx-xxx-xxx-xxx not found."
}
```

### Common Errors

**404 Not Found**
```json
{"detail": "User with ID xxx not found."}
```

**422 Validation Error**
```json
{"detail": "Invalid file type. Allowed types: PDF, DOCX, DOC, TXT"}
```

**503 Service Unavailable**
```json
{"detail": "Agent unreachable: Connection failed"}
```

---

## JavaScript/Fetch Examples

### Create User
```javascript
const response = await fetch('http://localhost:8000/api/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    first_name: 'John',
    last_name: 'Doe'
  })
});
const user = await response.json();
```

### Upload Resume
```javascript
const formData = new FormData();
formData.append('file', resumeFile);

const response = await fetch(
  `http://localhost:8000/api/users/${userId}/resume`,
  {
    method: 'POST',
    body: formData
  }
);
const result = await response.json();
```

### Analyze Job
```javascript
const response = await fetch('http://localhost:8000/api/resume/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ job_url: jobUrl })
});
const analysis = await response.json();
```

---

## Environment Variables

```bash
# Required
AGENT_BASE_URL=http://localhost:8001

# Optional
SUPABASE_RESUME_BUCKET=resumes
DATABASE_URL=sqlite:///./db.sqlite3
```

---

## File Size Limits

Currently no limits are enforced. For production:
- Resume files: < 10MB recommended
- API payload: < 1MB
- Rate limit: 100 requests/minute per IP

---

## CORS Configuration

Development: All origins allowed
```
Access-Control-Allow-Origin: *
```

Production: Restrict to frontend domain
```
Access-Control-Allow-Origin: https://yourdomain.com
```

---

## Common Integration Patterns

### Pattern 1: Create User + Upload Resume
```javascript
// 1. Create user
const user = await createUser(userData);
const userId = user.user_id;

// 2. Upload resume
await uploadResume(userId, resumeFile);

// 3. Now ready for analysis
```

### Pattern 2: Analyze + Generate Answer
```javascript
// Get job URL from user input
const jobUrl = getUserJobUrl();

// 1. Analyze resume
const analysis = await analyzeResume(jobUrl);
showMatchScore(analysis.match_percentage);

// 2. Generate answer if needed
if (userNeedsAnswer) {
  const answer = await generateAnswer(jobUrl, question);
  showGeneratedAnswer(answer.answer);
}
```

---

## Troubleshooting

### "Connection refused"
- Backend not running: `python -m uvicorn app.main:app --reload`
- Wrong port: Check BASE_URL is correct

### "Invalid file type"
- File must be: PDF, DOCX, DOC, or TXT
- Check file extension and MIME type

### "Agent unreachable"
- Agent service not running on port 8001
- Check `AGENT_BASE_URL` environment variable
- Verify Agent is accessible: `http://localhost:8001/health`

### "User not found"
- Wrong user_id format
- User was created in different session (mock storage)
- ID not returned from create endpoint

---

## API Testing Tools

### Recommended Tools
- **Postman** - GUI for API testing
- **curl** - Command line testing
- **Thunder Client** - VS Code extension
- **RESTClient** - VS Code extension

### Quick Test
```bash
# Check if API is running
curl http://localhost:8000/health

# Should return
{"status": "ok"}
```

---

## Performance Tips

1. **Cache user_id** in localStorage after creation
2. **Debounce** analysis requests while typing job URL
3. **Batch** multiple updates into single PATCH request
4. **Reuse** analysis results for same job URL
5. **Lazy load** recommendations below fold

---

## Rate Limits (Future)

When implemented:
- 100 requests/minute per IP
- 1000 requests/day per user
- 10 concurrent requests max

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-04-19 | Initial implementation |

---

## Need Help?

📖 **Full Documentation:** See `API_ENDPOINTS.md`
🔗 **Integration Guide:** See `FRONTEND_INTEGRATION_GUIDE.md`
🏗️ **Architecture:** See `ARCHITECTURE.md`
💻 **Examples:** See `examples_api_usage.py` and `API_EXAMPLES.sh`

---

**Last Updated:** April 19, 2024
