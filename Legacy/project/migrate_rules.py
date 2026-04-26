#!/usr/bin/env python3
"""
Migration Script: Re-normalize all rules in PostgreSQL

Fetches all rules, re-normalizes and canonicalizes them, updates DB.
Ensures:
- Deterministic output
- No data loss
- Safe transactions
- Error logging with skip behavior
- No changes to rule_id or version

Usage:
    python migrate_rules.py
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import sys
from datetime import datetime

# Import normalization functions
from utils.normalizer import normalize_rule
from utils.canonicalizer import canonicalize_rule


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():
    """Establish connection to PostgreSQL database."""
    from config import DB_CONFIG
    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# MIGRATION LOGIC
# ============================================================

def migrate_rules():
    """
    Main migration function.
    
    Returns:
        (success_count, skip_count, failed_count)
    """
    
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # ✅ Step 1: Fetch all rules
        print(f"\n{'='*70}")
        print(f"RULE MIGRATION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        cursor.execute("""
            SELECT rule_id, version, canonical_rule 
            FROM rules 
            ORDER BY rule_id, version DESC
        """)
        
        all_rules = cursor.fetchall()
        
        if not all_rules:
            print("❌ No rules found in database")
            return 0, 0, 0
        
        print(f"📚 Found {len(all_rules)} rules to migrate\n")
        
        # ✅ Step 2: Process each rule
        success_count = 0
        skip_count = 0
        failed_rules = []
        
        for idx, rule_record in enumerate(all_rules, 1):
            rule_id = rule_record["rule_id"]
            version = rule_record["version"]
            canonical_rule = rule_record["canonical_rule"]
            
            try:
                # Parse canonical_rule if it's a JSON string
                if isinstance(canonical_rule, str):
                    try:
                        rule_dict = json.loads(canonical_rule)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  [{idx}/{len(all_rules)}] {rule_id} (v{version}): Invalid JSON - SKIPPED")
                        skip_count += 1
                        failed_rules.append({
                            "rule_id": rule_id,
                            "version": version,
                            "error": f"Invalid JSON: {str(e)}"
                        })
                        continue
                else:
                    rule_dict = canonical_rule
                
                # ✅ Step 3: Normalize
                try:
                    normalized = normalize_rule(rule_dict)
                except Exception as e:
                    print(f"⚠️  [{idx}/{len(all_rules)}] {rule_id} (v{version}): Normalize failed - SKIPPED")
                    print(f"    Error: {str(e)}")
                    skip_count += 1
                    failed_rules.append({
                        "rule_id": rule_id,
                        "version": version,
                        "error": f"Normalization failed: {str(e)}"
                    })
                    continue
                
                # ✅ Step 4: Canonicalize
                try:
                    canonicalized = canonicalize_rule(normalized)
                except Exception as e:
                    print(f"⚠️  [{idx}/{len(all_rules)}] {rule_id} (v{version}): Canonicalize failed - SKIPPED")
                    print(f"    Error: {str(e)}")
                    skip_count += 1
                    failed_rules.append({
                        "rule_id": rule_id,
                        "version": version,
                        "error": f"Canonicalization failed: {str(e)}"
                    })
                    continue
                
                # ✅ Step 5: Update database (safe transaction)
                cursor.execute("""
                    UPDATE rules 
                    SET canonical_rule = %s 
                    WHERE rule_id = %s AND version = %s
                """, (
                    json.dumps(canonicalized),
                    rule_id,
                    version
                ))
                
                conn.commit()
                
                print(f"✅ [{idx}/{len(all_rules)}] {rule_id} (v{version}) → Updated")
                success_count += 1
            
            except psycopg2.Error as e:
                conn.rollback()
                print(f"❌ [{idx}/{len(all_rules)}] {rule_id} (v{version}): Database error - SKIPPED")
                print(f"    Error: {str(e)}")
                skip_count += 1
                failed_rules.append({
                    "rule_id": rule_id,
                    "version": version,
                    "error": f"Database error: {str(e)}"
                })
            
            except Exception as e:
                conn.rollback()
                print(f"❌ [{idx}/{len(all_rules)}] {rule_id} (v{version}): Unexpected error - SKIPPED")
                print(f"    Error: {str(e)}")
                skip_count += 1
                failed_rules.append({
                    "rule_id": rule_id,
                    "version": version,
                    "error": f"Unexpected error: {str(e)}"
                })
        
        # ✅ Step 6: Print summary
        print(f"\n{'='*70}")
        print(f"MIGRATION COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        print(f"\n📊 SUMMARY:")
        print(f"   ✅ Success: {success_count}")
        print(f"   ⏭️  Skipped: {skip_count}")
        print(f"   ❌ Failed: {len(failed_rules)}")
        print(f"   📈 Total updated: {success_count}/{len(all_rules)}")
        
        # Print failed rules
        if failed_rules:
            print(f"\n⚠️  FAILED RULES ({len(failed_rules)}):")
            for failed in failed_rules:
                print(f"   - {failed['rule_id']} (v{failed['version']})")
                print(f"     Error: {failed['error']}")
        
        print(f"\n{'='*70}\n")
        
        return success_count, skip_count, len(failed_rules)
    
    except psycopg2.Error as e:
        print(f"\n❌ Database connection error: {e}")
        return 0, 0, 0
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0, 0
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# VERIFICATION (OPTIONAL)
# ============================================================

def verify_migration(sample_count=3):
    """
    Verify migration by checking a sample of updated rules.
    
    Args:
        sample_count: Number of rules to verify
    """
    
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"\n{'='*70}")
        print("VERIFICATION: Sampling updated rules")
        print(f"{'='*70}\n")
        
        cursor.execute("""
            SELECT rule_id, version, canonical_rule 
            FROM rules 
            ORDER BY version DESC 
            LIMIT %s
        """, (sample_count,))
        
        sample_rules = cursor.fetchall()
        
        for idx, rule in enumerate(sample_rules, 1):
            rule_id = rule["rule_id"]
            version = rule["version"]
            canonical_rule = rule["canonical_rule"]
            
            if isinstance(canonical_rule, str):
                canonical_rule = json.loads(canonical_rule)
            
            print(f"[{idx}] Rule: {rule_id} (v{version})")
            print(f"    Structure: {json.dumps(canonical_rule, indent=6)}\n")
        
        print(f"{'='*70}\n")
    
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# ROLLBACK (SAFETY)
# ============================================================

def rollback_migration():
    """
    Safety function: Re-fetch rules from original source.
    (Should be done before running if you have backups)
    """
    
    print("\n⚠️  ROLLBACK FUNCTION")
    print("To rollback, restore the 'canonical_rule' column from backup.")
    print("Or restore the entire 'rules' table from PostgreSQL backup.")
    print("\nExample:")
    print("  pg_restore -d regtech backup.sql")
    print()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        # Run migration
        success, skipped, failed = migrate_rules()
        
        # Optional: Verify sample of updated rules
        if success > 0:
            response = input("\nVerify migration with sample rules? (y/n): ").strip().lower()
            if response == "y":
                verify_migration(sample_count=3)
        
        # Exit status
        if failed == 0 and success > 0:
            print("✅ Migration completed successfully!")
            sys.exit(0)
        else:
            print(f"⚠️  Migration completed with issues: {failed} failed, {skipped} skipped")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n❌ Migration interrupted by user")
        sys.exit(1)
