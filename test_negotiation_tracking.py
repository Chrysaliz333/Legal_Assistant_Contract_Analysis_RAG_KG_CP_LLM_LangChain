"""
Test negotiation tracking functionality
"""

from src.services.negotiation_tracker import NegotiationTracker

# Create tracker
tracker = NegotiationTracker()

# Create a negotiation
negotiation_id = "acme_saas_2025"
tracker.create_negotiation(negotiation_id, "Acme Corp SaaS Agreement")

print("✅ Created negotiation: Acme Corp SaaS Agreement")

# Add version 1 (initial draft)
v1_text = """
MASTER SERVICES AGREEMENT

1. LIABILITY CAP
Contractor's liability shall not exceed 1× annual fees.

2. TERMINATION
Either party may terminate with 30 days notice.
"""

v1 = tracker.add_version(
    negotiation_id,
    v1_text,
    uploaded_by='internal',
    notes='Initial draft from legal team'
)

print(f"✅ Added Version 1: {v1.version_id}")

# Add version 2 (counterparty response)
v2_text = """
MASTER SERVICES AGREEMENT

1. LIABILITY CAP
Contractor's liability shall not exceed 1.5× annual fees.

2. TERMINATION
Either party may terminate with 60 days notice.

3. ARBITRATION
All disputes shall be resolved through binding arbitration.
"""

v2 = tracker.add_version(
    negotiation_id,
    v2_text,
    uploaded_by='counterparty',
    notes='Counterparty increased liability cap and added arbitration clause'
)

print(f"✅ Added Version 2: {v2.version_id}")

# Compare versions
comparison = tracker.compare_versions(v1.version_id, v2.version_id)

print("\n" + "="*80)
print("VERSION COMPARISON")
print("="*80)

print(f"\nVersion 1 → Version 2")
print(f"Additions: {comparison['summary']['additions']}")
print(f"Deletions: {comparison['summary']['deletions']}")
print(f"Total changes: {comparison['summary']['total_changes']}")

print("\n" + "-"*80)
print("UNIFIED DIFF:")
print("-"*80)
print(comparison['diff_unified'])

# Get timeline
timeline = tracker.get_negotiation_timeline(negotiation_id)

print("\n" + "="*80)
print("NEGOTIATION TIMELINE")
print("="*80)

for entry in timeline:
    print(f"\nVersion {entry['version_number']} ({entry['uploaded_by']})")
    print(f"  Uploaded: {entry['uploaded_at']}")
    if entry['notes']:
        print(f"  Notes: {entry['notes']}")

print("\n✅ Negotiation tracking test complete!")
print(f"📁 Data saved in: negotiations/{negotiation_id}_*")
