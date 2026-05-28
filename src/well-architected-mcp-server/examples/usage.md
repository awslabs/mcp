# Usage Examples

## Example Prompts for AI Assistants

### Architecture Review
```
Using the Well-Architected BP server, what are the high-risk security best practices
I should review for a new web application?
```

### Cost Optimization
```
Show me all cost optimization best practices related to compute resources.
```

### Specific Practice Details
```
Get details for SEC01-BP01 and explain how to implement it.
```

### Related Practices
```
What best practices are related to SEC02-BP04?
```

### GenAI Workloads
```
What are the security best practices specific to generative AI workloads?
```

## Expected Results

### Total Best Practices Available
- **356 total best practices** across all pillars and lenses
- Framework: 307 best practices
- Generative AI Lens: 49 best practices

### By Pillar
- OPERATIONAL_EXCELLENCE: 78
- SECURITY: 73
- RELIABILITY: 75
- PERFORMANCE_EFFICIENCY: 40
- COST_OPTIMIZATION: 57
- SUSTAINABILITY: 33

### Risk Levels
- HIGH: Critical practices that should be prioritized
- MEDIUM: Important practices for robust architectures
- LOW: Optimization and enhancement practices

## Sample Best Practice Structure

```json
{
  "id": "SEC01-BP01",
  "title_full": "SEC01-BP01 Separate workloads using accounts",
  "title": "Separate workloads using accounts",
  "pillar": "SECURITY",
  "lens": "FRAMEWORK",
  "href": "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/...",
  "area": [
    "Security Foundations",
    "AWS account management and separation"
  ],
  "description": "Establish common guardrails and isolation...",
  "outcome": "",
  "risk": "HIGH",
  "relatedIds": ["SEC02-BP04"]
}
```
