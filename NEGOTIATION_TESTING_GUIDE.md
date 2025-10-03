# Negotiation Tracking - Testing Guide

## Test Files Created

✅ **Version 1**: `sample_msa.txt` (Original contract)
✅ **Version 2**: `sample_msa_v2.txt` (Counterparty response with changes)

## Key Changes Between Versions

| Clause | Version 1 | Version 2 | Change Type |
|--------|-----------|-----------|-------------|
| **Liability Cap** | 1× annual fees | 1.5× annual fees | ⬆️ Increased |
| **IP Ownership** | Contractor owns, Client gets revocable license | Joint ownership, perpetual license | ✅ Improved |
| **Termination Notice** | 30 days | 60 days | ⬆️ Extended |
| **Payment Deadline** | 90 days after termination | 30 days after termination | ⬇️ Reduced |
| **Confidentiality** | 2 years survival | 5 years survival | ⬆️ Extended |
| **Data Transfers** | No notice required | Prior written notice required | ✅ Added protection |
| **Payment Terms** | 60 days, 2% interest | 30 days, 1.5% interest | ⬇️ Faster payment |
| **Refunds** | Non-refundable | Pro-rated refunds allowed | ✅ Added |
| **Governing Law** | Cayman Islands, Russian | Delaware US, English | ✅ Changed jurisdiction |
| **Indemnification** | Client indemnifies Contractor only | Mutual indemnification | ✅ Balanced |
| **Assignment** | Contractor can freely assign | Mutual consent required | ✅ Balanced |
| **Renewal Notice** | 180 days | 90 days | ⬇️ Reduced |
| **Fee Increase** | Up to 25% unilateral | Max 10% with consent | ✅ Capped |
| **SLA Uptime** | 95% annual, 2% credit | 99.5% monthly, 5% escalating | ⬆️ Improved |

## Testing Workflow

### Step 1: Upload Version 1 (Initial Draft)

1. Open app at http://localhost:8502
2. **Negotiation**: Click "+ Start New Negotiation"
3. **Title**: Enter "Acme Corp MSA Negotiation"
4. Click **Create**
5. Upload `sample_msa.txt`
6. **This version is from**: Select `internal`
7. **Notes**: Enter "Initial draft from legal team"
8. Click **🚀 Analyze Contract**

**Expected Results:**
- ✅ Analysis completes (10-30 seconds)
- ✅ Shows findings (likely 4-8 issues)
- ✅ Success message: "Saved as acme_corp_msa_v1" (or similar)
- ✅ Timeline shows 1 version

### Step 2: Upload Version 2 (Counterparty Response)

1. Same negotiation should be selected in sidebar
2. Upload `sample_msa_v2.txt`
3. **This version is from**: Select `counterparty`
4. **Notes**: Enter "Counterparty improved liability, IP, and SLA terms"
5. Click **🚀 Analyze Contract**

**Expected Results:**
- ✅ Analysis completes
- ✅ Shows findings for v2
- ✅ Success message: "Saved as acme_corp_msa_v2" (or similar)
- ✅ Timeline shows 2 versions

### Step 3: Review Timeline

1. Scroll to **📋 Negotiation Timeline** section
2. Expand each version

**Expected Results:**
- ✅ Version 1 shows:
  - Uploaded by: Internal
  - Notes: "Initial draft from legal team"
  - Analysis summary (findings count)
- ✅ Version 2 shows:
  - Uploaded by: Counterparty
  - Notes: "Counterparty improved liability, IP, and SLA terms"
  - Analysis summary (findings count)

### Step 4: Compare Versions

1. Scroll to **🔀 Compare Versions** section
2. **Base Version**: Select "Version 1"
3. **Compare To**: Select "Version 2"
4. Click **Compare Selected Versions**

**Expected Results:**
- ✅ Shows unified diff output
- ✅ Additions show with `+` prefix (green background)
- ✅ Deletions show with `-` prefix (red background)
- ✅ Statistics show:
  - Additions: ~15-20 lines
  - Deletions: ~15-20 lines
  - Total changes: ~30-40 lines

**Key Changes to Look For in Diff:**
```diff
-Contractor's total liability under this Agreement shall not exceed the amount of fees paid by Client
+Contractor's total liability under this Agreement shall not exceed 1.5× the amount of fees paid by Client

-All work product... shall remain the property of Contractor. Client is granted a non-exclusive, revocable license
+All work product... shall be jointly owned by Contractor and Client. Client is granted a perpetual, irrevocable license

-Either party may terminate this Agreement... upon thirty (30) days prior written notice
+Either party may terminate this Agreement... upon sixty (60) days prior written notice

-This Agreement shall be governed by the laws of the Cayman Islands... in Russian
+This Agreement shall be governed by the laws of Delaware, United States... in English
```

### Step 5: Test Duplicate Detection

1. Try uploading `sample_msa.txt` again (same as v1)
2. Select any "from" option
3. Click **🚀 Analyze Contract**

**Expected Results:**
- ⚠️ Warning message: "Duplicate version detected (identical to version 1)"
- ✅ No new version created

## Success Criteria

✅ All features working:
1. Create negotiation
2. Upload multiple versions with metadata
3. View timeline with all versions
4. Compare any two versions
5. Duplicate detection prevents identical uploads
6. Each version stores analysis results
7. Timeline shows analysis summaries

## Known Issues to Watch For

⚠️ **Potential Issues:**
1. **Import Error**: If `NegotiationTracker` import fails, check `src/services/negotiation_tracker.py` exists
2. **Session State**: If negotiation resets on page refresh, this is expected (Streamlit behavior)
3. **File Storage**: Check `negotiations/` directory is created with JSON files
4. **Diff Display**: If diff doesn't render correctly, check Streamlit version supports `st.code(language='diff')`

## Files Created During Test

After completing the test, you should see:

```
negotiations/
├── acme_corp_msa_negotiation_negotiation.json    # Negotiation metadata
├── acme_corp_msa_negotiation_v1.json             # Version 1 data
└── acme_corp_msa_negotiation_v2.json             # Version 2 data
```

Each version file contains:
- Full contract text
- Upload metadata (timestamp, uploaded_by, notes)
- SHA-256 hash (for duplicate detection)
- Analysis results from unified agent

## Next Steps After Testing

1. ✅ If all tests pass → Deploy to Streamlit Cloud
2. ⚠️ If bugs found → Create bug list and fix systematically
3. 📊 If performance issues → Optimize diff generation or limit version count

## Manual Testing Checklist

- [ ] Create new negotiation
- [ ] Upload v1 with "internal" tag and notes
- [ ] Verify v1 analysis completes
- [ ] Verify v1 appears in timeline
- [ ] Upload v2 with "counterparty" tag and notes
- [ ] Verify v2 analysis completes
- [ ] Verify both v1 and v2 appear in timeline
- [ ] Compare v1 vs v2 and verify diff shows changes
- [ ] Try uploading duplicate (expect warning)
- [ ] Check `negotiations/` directory for JSON files
- [ ] Verify analysis summaries show in timeline
- [ ] Test selecting different negotiations from sidebar
