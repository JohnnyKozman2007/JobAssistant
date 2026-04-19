# Frontend-Backend API Integration Guide

This document provides frontend developers with information needed to integrate with the JobAssistant Backend API.

## API Base URL

Development: `http://localhost:8000/api`

## Quick Start

### 1. Create User (Onboarding Step 1)

**When:** User completes initial profile setup
**Frontend File:** `Frontend/app/onboarding/step-1/page.tsx`

```javascript
const response = await fetch('http://localhost:8000/api/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: formData.email,
    first_name: formData.firstName,
    last_name: formData.lastName,
    phone_number: formData.phone,
    location: formData.location,
    desired_job_title: formData.desiredJob,
    years_of_experience: parseInt(formData.experience),
  }),
});

const user = await response.json();
// Save user.user_id for subsequent calls
sessionStorage.setItem('userId', user.user_id);
```

### 2. Upload Resume (Onboarding Step 3)

**When:** User uploads their resume file
**Frontend File:** `Frontend/app/onboarding/step-3/page.tsx`

```javascript
const formData = new FormData();
formData.append('file', resumeFile); // File object from input

const response = await fetch(
  `http://localhost:8000/api/users/${userId}/resume`,
  {
    method: 'POST',
    body: formData, // Note: no Content-Type header needed for FormData
  }
);

const result = await response.json();
console.log('Resume uploaded:', result.filename);
```

### 3. Analyze Job & Resume (Dashboard)

**When:** User views a job and wants to see match analysis
**Frontend File:** `Frontend/app/dashboard/page.tsx`

```javascript
const jobUrl = 'https://linkedin.com/jobs/view/...';

const response = await fetch('http://localhost:8000/api/resume/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ job_url: jobUrl }),
});

const analysis = await response.json();
// {
//   match_percentage: 78.5,
//   key_matches: [...],
//   gaps: [...],
//   recommendations: [...]
// }
```

### 4. Generate Tailored Answer (Dashboard)

**When:** User wants AI-generated answer to interview question
**Frontend File:** `Frontend/app/dashboard/page.tsx`

```javascript
const jobUrl = 'https://linkedin.com/jobs/view/...';
const question = 'Tell us about your experience with...';

const response = await fetch('http://localhost:8000/api/generate/answer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    job_url: jobUrl,
    user_question: question,
  }),
});

const result = await response.json();
// {
//   answer: "Generated tailored answer...",
//   relevance_score: 92.0
// }
```

### 5. Update User Profile (Profile Page)

**When:** User edits their profile
**Frontend File:** `Frontend/app/profile/page.tsx`

```javascript
const response = await fetch(
  `http://localhost:8000/api/users/${userId}`,
  {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      // Only include fields that changed
      desired_job_title: newTitle,
      location: newLocation,
    }),
  }
);

const updated = await response.json();
```

---

## Component Integration Examples

### JobAnalyzer Component

```typescript
// Frontend/components/JobAnalyzer.tsx

interface AnalysisResult {
  match_percentage: number;
  key_matches: string[];
  gaps: string[];
  recommendations: string[];
}

export async function analyzeJob(jobUrl: string): Promise<AnalysisResult> {
  const response = await fetch('http://localhost:8000/api/resume/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_url: jobUrl }),
  });

  if (!response.ok) {
    throw new Error(`Analysis failed: ${response.statusText}`);
  }

  return response.json();
}
```

### ResumeUploader Component

```typescript
// Frontend/components/ResumeUploader.tsx

export async function uploadResume(
  userId: string,
  file: File
): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(
    `http://localhost:8000/api/users/${userId}/resume`,
    {
      method: 'POST',
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error('Resume upload failed');
  }

  const result = await response.json();
  console.log(`Resume uploaded: ${result.filename}`);
}
```

### MatchScoreCard Component

```typescript
// Frontend/components/MatchScoreCard.tsx

interface Props {
  matchPercentage: number;
  keyMatches: string[];
  gaps: string[];
  recommendations: string[];
}

export function MatchScoreCard({
  matchPercentage,
  keyMatches,
  gaps,
  recommendations,
}: Props) {
  return (
    <div className="match-score-card">
      <div className="score-circle">{matchPercentage}%</div>
      
      <div className="section">
        <h3>Key Matches</h3>
        <ul>
          {keyMatches.map((match, i) => (
            <li key={i}>{match}</li>
          ))}
        </ul>
      </div>

      <div className="section">
        <h3>Gaps to Address</h3>
        <ul>
          {gaps.map((gap, i) => (
            <li key={i}>{gap}</li>
          ))}
        </ul>
      </div>

      <div className="section">
        <h3>Recommendations</h3>
        <ul>
          {recommendations.map((rec, i) => (
            <li key={i}>{rec}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

### AIAnswerGenerator Component

```typescript
// Frontend/components/AIAnswerGenerator.tsx

interface AnswerResult {
  answer: string;
  relevance_score: number;
}

export async function generateAnswer(
  jobUrl: string,
  question: string
): Promise<AnswerResult> {
  const response = await fetch('http://localhost:8000/api/generate/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_url: jobUrl,
      user_question: question,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to generate answer');
  }

  return response.json();
}
```

---

## Error Handling

All endpoints return error responses in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors:

**404 Not Found:**
```json
{
  "detail": "User with ID xxx-xxx-xxx-xxx not found."
}
```

**422 Unprocessable Entity:**
```json
{
  "detail": "Invalid file type. Allowed types: PDF, DOCX, DOC, TXT"
}
```

**503 Service Unavailable:**
```json
{
  "detail": "Agent unreachable: Connection failed"
}
```

### Error Handling Pattern:

```javascript
try {
  const response = await fetch(apiUrl, options);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API request failed');
  }
  
  return await response.json();
} catch (error) {
  console.error('API Error:', error);
  // Show user-friendly error message
}
```

---

## State Management

### Recommended Flow:

```
1. User logs in / creates account
   ↓
2. POST /api/users → Save user_id to localStorage/sessionStorage
   ↓
3. User uploads resume
   ↓
4. POST /api/users/{user_id}/resume
   ↓
5. User searches jobs / views opportunities
   ↓
6. POST /api/resume/analyze (for each job view)
   POST /api/generate/answer (when requesting answer)
```

### Storage Recommendations:

```javascript
// Save after user creation
sessionStorage.setItem('jobAssistant.userId', user.user_id);

// Or use state management (Zustand, Redux, Context):
const userStore = create((set) => ({
  userId: null,
  setUserId: (id) => set({ userId: id }),
}));
```

---

## Rate Limiting & Performance

Currently no rate limiting is implemented. For production:
- Consider adding rate limiting on analysis endpoints
- Add debouncing for rapid API calls
- Cache analysis results when possible
- Implement request timeouts (120s for agent calls)

---

## CORS Considerations

CORS is configured to allow all origins in development:
```python
allow_origins=["*"]
allow_methods=["*"]
allow_headers=["*"]
```

For production, restrict to specific frontend domain:
```python
allow_origins=["https://yourdomain.com"]
```

---

## Data Contracts

All request/response formats are documented in `API_ENDPOINTS.md` in the Backend folder.

### Key Response Formats:

**User Profile:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2024-04-19T10:30:00Z",
  "updated_at": "2024-04-19T10:30:00Z",
  "has_resume": true
}
```

**Resume Analysis:**
```json
{
  "match_percentage": 78.5,
  "key_matches": ["skill1", "skill2"],
  "gaps": ["skill3", "skill4"],
  "recommendations": ["rec1", "rec2"]
}
```

**Generated Answer:**
```json
{
  "answer": "Generated answer text...",
  "relevance_score": 92.0
}
```

---

## Next Steps

1. **Integrate** these endpoints into the onboarding flow
2. **Test** with the provided curl examples or Python client
3. **Handle errors** gracefully with user-friendly messages
4. **Store** user_id securely after creation
5. **Display** analysis results in Dashboard components
6. **Show** generated answers in Interview prep sections
