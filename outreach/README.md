# Outreach Folder

This folder contains customer outreach data.

**NOT committed to git** (see .gitignore) - keep lead info private.

## Files

- `leads.json` - List of potential customers you found
- `responses.json` - Track who replied
- `sent.json` - Track emails already sent

## Lead Format

```json
{
  "leads": [
    {
      "email": "person@example.com",
      "name": "John",
      "reason": "Housing activist in Echo Park",
      "source": "LinkedIn",
      "status": "pending"
    }
  ]
}
```
