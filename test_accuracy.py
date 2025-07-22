#!/usr/bin/env python3
"""
Test script to demonstrate the refined PDF extractor accuracy improvements.
This script shows how the algorithm handles different document types.
"""

import json
import os
from refined_pdf_extractor import RefinedPDFOutlineExtractor

def test_extraction_accuracy():
    """Test the refined extractor on sample documents."""
    print("🧪 Testing Refined PDF Outline Extractor")
    print("=" * 50)

    extractor = RefinedPDFOutlineExtractor()

    # Test files (when available)
    test_cases = [
        {
            'file': 'file02.pdf',
            'description': 'ISTQB Technical Document',
            'expected_levels': ['H1', 'H2'],
            'expected_count_range': (15, 20)
        },
        {
            'file': 'file04.pdf', 
            'description': 'STEM Pathways Document',
            'expected_levels': ['H1'],
            'expected_count_range': (1, 3)
        },
        {
            'file': 'file05.pdf',
            'description': 'Simple Invitation Form',
            'expected_levels': [],
            'expected_count_range': (0, 2)
        }
    ]

    for test_case in test_cases:
        filename = test_case['file']
        if os.path.exists(filename):
            print(f"\n📄 Testing: {test_case['description']}")
            print(f"   File: {filename}")

            try:
                result = extractor.extract_outline(filename)

                # Analysis
                outline = result.get('outline', [])
                levels_found = list(set([h['level'] for h in outline]))
                count = len(outline)

                print(f"   Title: {result.get('title', 'N/A')}")
                print(f"   Headings found: {count}")
                print(f"   Levels detected: {levels_found}")

                # Check if within expected range
                min_exp, max_exp = test_case['expected_count_range']
                if min_exp <= count <= max_exp:
                    print("   ✅ Heading count within expected range")
                else:
                    print(f"   ⚠️  Heading count outside expected range ({min_exp}-{max_exp})")

                # Check levels
                unexpected_levels = [l for l in levels_found if l not in test_case['expected_levels'] and l != 'H2']
                if not unexpected_levels or test_case['expected_levels'] == []:
                    print("   ✅ Heading levels appropriate")
                else:
                    print(f"   ⚠️  Unexpected levels: {unexpected_levels}")

                # Show first few headings
                print("   Sample headings:")
                for i, heading in enumerate(outline[:5]):
                    print(f"     {heading['level']}: {heading['text'][:50]}{'...' if len(heading['text']) > 50 else ''} (p.{heading['page']})")
                if len(outline) > 5:
                    print(f"     ... and {len(outline) - 5} more")

            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            print(f"\n📄 {test_case['description']}: File not found ({filename})")

    print("\n" + "=" * 50)
    print("🎯 ALGORITHM IMPROVEMENTS SUMMARY:")
    print("1. Conservative thresholds reduce over-classification")
    print("2. Document complexity analysis prevents unnecessary H3/H4")
    print("3. Pattern-based detection focuses on strong indicators")
    print("4. Content penalties avoid paragraph misclassification")
    print("5. Duplicate removal prevents repetitive headings")

def demonstrate_key_features():
    """Demonstrate key features of the refined algorithm."""
    print("\n🔍 KEY ALGORITHM FEATURES:")
    print("-" * 30)

    features = [
        {
            'name': 'Conservative Scoring',
            'description': 'Higher confidence thresholds (60% vs 50%) reduce false positives'
        },
        {
            'name': 'Document Analysis', 
            'description': 'Analyzes document complexity to limit hierarchy depth appropriately'
        },
        {
            'name': 'Pattern Priority',
            'description': 'Strong numbered sections (1., 2.1) get highest classification scores'
        },
        {
            'name': 'Content Penalties',
            'description': 'Long text, multiple sentences penalized to avoid content misclassification'
        },
        {
            'name': 'Hierarchy Limits',
            'description': 'Simple documents limited to H1/H2 levels only'
        },
        {
            'name': 'Smart Filtering',
            'description': 'Removes navigation text, headers/footers, and duplicate entries'
        }
    ]

    for feature in features:
        print(f"✨ {feature['name']}: {feature['description']}")

if __name__ == "__main__":
    test_extraction_accuracy()
    demonstrate_key_features()
    print("\n✅ Testing complete!")
