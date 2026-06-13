import json
import re
from typing import Optional

from openai import OpenAI

from app.config import settings
from app.services.chunking import chunk_text
from app.services.indian_legal_knowledge import INDIAN_LEGAL_SYSTEM_PROMPT

SYSTEM_PROMPT = f"""{INDIAN_LEGAL_SYSTEM_PROMPT}

## YOUR TASK
Extract and classify every clause from the contract text below. Assess risk based on INDIAN law.

Return a JSON object with a "clauses" array. Each clause:
- clause_type: type of clause
- clause_text: exact text of the clause
- section_header: section heading
- risk_level: high|medium|low|info
- risk_reason: why risky under Indian law
- suggested_redline: suggested alternative language

Only return valid JSON, no other text."""

CLAUSE_KEYWORDS_FALLBACK = {
    "Non-Compete": ["non-compete", "non compete", "not compete", "restraint of trade", "shall not provide similar services", "not provide services"],
    "Indemnification": ["indemnif", "hold harmless", "indemnity"],
    "Limitation of Liability": ["limitation of liab", "cap on liab", "aggregate liab", "maximum liab", "total liability"],
    "Governing Law": ["governing law", "governed by", "laws of", "construed in accordance"],
    "Jurisdiction": ["jurisdiction", "courts at", "subject to jurisdiction", "exclusive jurisdiction"],
    "Arbitration": ["arbitration", "arbitrator", "arbitral", "seat of arbitration"],
    "Termination": ["terminat", "termination", "terminate", "notice period"],
    "Intellectual Property": ["intellectual property", "ip rights", "ip vest", "vest in", "copyright", "patent"],
    "Confidentiality": ["confidential", "non-disclosure", "proprietary information", "confidential information"],
    "Data Protection": ["data protection", "personal data", "dpdp", "privacy", "data breach", "personal information"],
    "Payment Terms": ["fee", "payment", "invoice", "payable", "rs.", "rupees", "consideration"],
    "Force Majeure": ["force majeure", "act of god", "frustration", "beyond reasonable control"],
    "Warranty": ["warrant", "represent", "guarantee", "warranty"],
    "Entire Agreement": ["entire agreement", "supersedes", "whole agreement", "merger clause"],
    "Non-Solicit": ["non-solicit", "solicit", "employ any employee", "not solicit"],
    "Liquidated Damages": ["liquidated damages", "penalty", "ld", "late fees"],
    "Dispute Resolution": ["dispute", "dispute resolution", "negotiation", "mediation"],
}

CLAUSE_KNOWLEDGE_BASE = {
    "Non-Compete": {
        "risk": "high",
        "statute": "Section 27, Indian Contract Act, 1872",
        "standard": "Post-employment non-compete clauses are void except when ancillary to sale of goodwill. Courts interpret strictly; restraints must be reasonable in time (max 6-12 months) and geography. Indian courts rarely enforce against low/mid-level employees.",
        "redline_hint": "Limit to 6-12 months, specific geography, and only for key personnel. Consider non-solicit as alternative."
    },
    "Indemnification": {
        "risk": "high",
        "statute": "Sections 124-125, Indian Contract Act, 1872",
        "standard": "Indian market standard: uncapped indemnity for IP infringement, breach of confidentiality, willful default. Other claims capped at contract value or 100% of fees paid. Survival period 3-6 years (vs 1-2 year US standard).",
        "redline_hint": "Cap at 100% of contract value for most claims. Unlimited for IP breach and fraud. Survival: 3 years minimum for Indian law."
    },
    "Limitation of Liability": {
        "risk": "high",
        "statute": "Indian Contract Act, 1872; Section 73 — Damages for breach",
        "standard": "Indian courts may not enforce limitation where there is willful default or fraud. Typical Indian IT contracts: liability cap at 100% of annual fees. No exclusion of consequential damages for IP breach or confidentiality breach.",
        "redline_hint": "Cap at 100% of contract value. Carve out: IP infringement, confidentiality breach, willful default, death/injury."
    },
    "Governing Law": {
        "risk": "high",
        "statute": "Indian Contract Act, 1872",
        "standard": "For India-facing contracts, governing law MUST be Indian law. Foreign governing law creates enforcement risk under Indian courts. Singapore/English law acceptable only for cross-border with arbitration seated in Singapore/London.",
        "redline_hint": "Specify: 'This Agreement shall be governed by and construed in accordance with the laws of India.'"
    },
    "Jurisdiction": {
        "risk": "medium",
        "statute": "Code of Civil Procedure, 1908, Section 20",
        "standard": "Indian courts prefer exclusive jurisdiction of courts in the city where contract is performed. 'Subject to jurisdiction of X courts' is common. Courts at registered office location of service provider is typical for IT/ITES.",
        "redline_hint": "Specify: 'Subject to the exclusive jurisdiction of courts at [City, India].'"
    },
    "Arbitration": {
        "risk": "medium",
        "statute": "Arbitration and Conciliation Act, 1996",
        "standard": "India is arbitration-friendly. Seat MUST be in India for domestic contracts. Common seats: Delhi, Mumbai, Bangalore. Institutional arbitration (SIAC, MCIA, ICA) preferred over ad-hoc. Sole arbitrator or panel of 3 for high-value.",
        "redline_hint": "Specify seat as a city in India (e.g., New Delhi). Add institutional rules reference. Specify appointing authority for default."
    },
    "Termination": {
        "risk": "medium",
        "statute": "Indian Contract Act, 1872, Sections 39, 55, 62-67",
        "standard": "Typical Indian IT contracts: 30 days notice for convenience. Immediate termination for material breach (with 30-day cure period). For-cause termination includes breach, insolvency, change of control. Post-termination assistance period 90 days standard.",
        "redline_hint": "30-day notice for convenience. Material breach with 30-60 day cure. Survival of IP, confidentiality, indemnification clauses."
    },
    "Intellectual Property": {
        "risk": "high",
        "statute": "Indian Copyright Act, 1957; Patents Act, 1970; Trade Marks Act, 1999",
        "standard": "Indian IT services: no automatic IP vesting. Must specify 'work made for hire' or 'assignment of IP.' Background IP remains with creator. Foreground IP vests in client upon full payment. Moral rights under Section 57 of Copyright Act cannot be assigned.",
        "redline_hint": "Specifically assign all IP developed under the contract. Include 'works made for hire' language. Distinguish background vs foreground IP."
    },
    "Confidentiality": {
        "risk": "medium",
        "statute": "Indian Contract Act, 1872; IT Act, 2000, Section 72",
        "standard": "Standard obligations: hold confidential, use only for purpose, disclose only to need-to-know employees. Term: during + 3-5 years post-termination. Exclusions: public knowledge, independently developed, required by law. Indian courts enforce well.",
        "redline_hint": "Define confidential information broadly. Term: during agreement + 5 years. Include required disclosure exception."
    },
    "Data Protection": {
        "risk": "high",
        "statute": "Digital Personal Data Protection Act, 2023; IT Act, 2000, Section 43A; SPDI Rules, 2011",
        "standard": "DPDP Act 2023 mandates: consent, purpose limitation, data minimization, reasonable security safeguards, breach notification to Board and affected persons. Cross-border data transfer now permitted to 'notified countries.' Significant data fiduciaries require DPO and audit.",
        "redline_hint": "Include data processing addendum referencing DPDP Act 2023. Define data fiduciary/processor roles. Specify breach notification: 72 hours to Board, affected persons without delay."
    },
    "Payment Terms": {
        "risk": "medium",
        "statute": "Indian Contract Act, 1872; Interest Act, 1978; GST Act, 2017",
        "standard": "Milestone-based or monthly billing. TDS under Section 194J (10%) or 194C (2%) as applicable. GST at 18% for most services. Late payment interest: 12-18% p.a. Interest rate > 24% may be struck down as penal. Payment within 30-45 days of invoice.",
        "redline_hint": "Specify payment within 30 days. Late payment interest at 18% p.a. TDS applicable as per Indian IT Act. GST extra as applicable."
    },
    "Force Majeure": {
        "risk": "low",
        "statute": "Section 56, Indian Contract Act, 1872 (Doctrine of Frustration)",
        "standard": "Indian law recognizes frustration of contract. Typical force majeure: act of God, war, pandemic, government action, labor unrest. Party must notify within 7-15 days. Suspension of obligations, not termination. If > 90 days, either party may terminate.",
        "redline_hint": "Define force majeure events explicitly including pandemic, government orders. Notice within 7 days. Right to terminate if force majeure exceeds 90 days."
    },
    "Warranty": {
        "risk": "medium",
        "statute": "Indian Contract Act, 1872; Sale of Goods Act, 1930",
        "standard": "Service warranties: work performed in professional manner, comply with specifications, use reasonable skill and care. 90-day correction period typical. IP warranty: services do not infringe third-party IP. Mutual warranty: authority to enter contract.",
        "redline_hint": "Limit warranty to 90 days from delivery. Exclusive remedy: re-performance or refund. Disclaimer for third-party content."
    },
    "Entire Agreement": {
        "risk": "low",
        "statute": "Indian Evidence Act, 1872, Section 91-92 (parol evidence rule)",
        "standard": "Standard merger clause. Prevents either party from claiming additional oral/written terms. Indian courts enforce strictly. Should specify that no modification except in writing signed by both parties.",
        "redline_hint": "Standard clause. Add: 'No amendment shall be effective unless in writing and signed by both parties.'"
    },
    "Non-Solicit": {
        "risk": "medium",
        "statute": "Section 27, Indian Contract Act, 1872",
        "standard": "Courts distinguish between employee non-solicit (restraint of trade) and customer non-solicit (may be valid). Employee non-solicit limited to 6-12 months during/post contract. Direct solicitation with existing employees vs general advertisement.",
        "redline_hint": "Limit to 12 months post-termination. Exclude general public advertisements. Direct solicitation only."
    },
    "GST_Compliance": {
        "risk": "high",
        "statute": "Central Goods and Services Tax Act, 2017",
        "standard": "Reverse charge mechanism may apply. E-invoicing for turnover > INR 5 Cr. GSTR-1, GSTR-3B filing mandatory. Place of supply rules critical for cross-state services. TDS under GST (2%) for government contracts.",
        "redline_hint": "Specify GST registration details. Clarify whether GST is included or extra. State: 'GST shall be paid on reverse charge basis where applicable.'"
    },
    "Liquidated Damages": {
        "risk": "medium",
        "statute": "Section 74, Indian Contract Act, 1872",
        "standard": "Indian courts will not award LD that is 'by way of penalty.' LD must be genuine pre-estimate of loss. Maximum 10-20% of contract value typically enforced. Courts can award reasonable compensation even if actual loss is less.",
        "redline_hint": "Cap LD at 10% of contract value. Specify: 'The parties agree that this is a genuine pre-estimate of loss.'"
    },
    "Dispute Resolution": {
        "risk": "medium",
        "statute": "Arbitration and Conciliation Act, 1996; Commercial Courts Act, 2015",
        "standard": "Multi-tier: negotiation (14-30 days) → mediation → arbitration. Commercial disputes > INR 3 Lakh must go to Commercial Court. Pre-institution mediation mandatory under Section 12A of Commercial Courts Act for suits.",
        "redline_hint": "Specify tiered dispute resolution: negotiation (15 days) → mediation (30 days) → arbitration seated in India."
    },
}

PRIORITY_MAP = {
    "high": {"label": "Must Fix", "color": "red"},
    "medium": {"label": "Should Fix", "color": "amber"},
    "low": {"label": "Review", "color": "blue"},
    "info": {"label": "Monitor", "color": "slate"},
}

COMPLIANCE_CHECKS = [
    {
        "name": "DPDP Act 2023 Compliance",
        "icon": "shield",
        "description": "Checks if contract addresses data protection obligations under India's new DPDP Act 2023 including consent, purpose limitation, breach notification, and cross-border transfer restrictions."
    },
    {
        "name": "GST Compliance",
        "icon": "receipt",
        "description": "Verifies GST registration details, tax invoice requirements, reverse charge mechanism, and e-invoicing compliance under CGST Act 2017."
    },
    {
        "name": "TDS Withholding",
        "icon": "bank",
        "description": "Confirms TDS provisions under Income Tax Act 1961 (Section 194J for professional services at 10%, Section 194C for contracts at 2%)."
    },
    {
        "name": "Arbitration & ADR",
        "icon": "scale",
        "description": "Validates arbitration clause meets Arbitration and Conciliation Act 1996 requirements including seat, venue, number of arbitrators, and appointing authority."
    },
    {
        "name": "Non-Compete Validity",
        "icon": "gavel",
        "description": "Assesses non-compete clauses against Section 27 Indian Contract Act — usually void post-employment except when ancillary to sale of goodwill."
    },
    {
        "name": "Limitation Period",
        "icon": "clock",
        "description": "Verifies that claim periods align with Limitation Act 1963 (3 years for contracts, 1 year for tort, 12 years for immovable property)."
    },
    {
        "name": "Interest & Penalties",
        "icon": "percent",
        "description": "Checks interest rates against usury laws and Section 74 Indian Contract Act (penalties must be genuine pre-estimate, not punitive)."
    },
    {
        "name": "Force Majeure",
        "icon": "cloud",
        "description": "Verifies force majeure clause aligns with Section 56 Indian Contract Act (doctrine of frustration) and covers pandemic, government orders, etc."
    },
]

COMPLIANCE_CHECK_KEYWORDS = {
    "DPDP Act 2023 Compliance": [
        "data protection", "personal data", "dpdp", "privacy", "data breach",
        "data fiduciary", "data processor", "consent", "cross-border",
        "digital personal data protection", "sensitive personal data"
    ],
    "GST Compliance": [
        "gst", "goods and services tax", "cgst", "sgst", "igst",
        "reverse charge", "tax invoice", "e-invoicing", "gstin"
    ],
    "TDS Withholding": [
        "tds", "tax deducted at source", "withholding tax", "194j",
        "194c", "section 194", "income tax act"
    ],
    "Arbitration & ADR": [
        "arbitration", "arbitrator", "arbitral", "conciliation",
        "arbitration and conciliation", "seat of arbitration", "award"
    ],
    "Non-Compete Validity": [
        "non-compete", "non compete", "restraint of trade",
        "shall not compete", "not compete", "section 27"
    ],
    "Limitation Period": [
        "limitation", "within 1 year", "within 3 years", "within 12 months",
        "limitation act", "statute of limitation"
    ],
    "Interest & Penalties": [
        "interest", "penalty", "liquidated damages", "late payment",
        "default interest", "penal interest"
    ],
    "Force Majeure": [
        "force majeure", "act of god", "frustration", "beyond reasonable control",
        "pandemic", "epidemic", "government order", "lockdown"
    ],
}


def extract_with_keywords(text: str) -> list[dict]:
    clauses = []
    seen_types = set()
    text_lower = text.lower()

    for clause_type, search_terms in CLAUSE_KEYWORDS_FALLBACK.items():
        if clause_type in seen_types:
            continue
        knowledge = CLAUSE_KNOWLEDGE_BASE.get(clause_type, {})
        best_match = None
        best_pos = None

        for term in search_terms:
            pos = text_lower.find(term.lower())
            if pos >= 0:
                if best_pos is None or pos < best_pos:
                    best_pos = pos
                    best_match = term

        if best_match is not None:
            seen_types.add(clause_type)
            pos = best_pos
            start = max(0, pos - 150)
            end = min(len(text), pos + 400)
            context = text[start:end].strip()

            section_header = "Unknown"
            lines = context.split("\n")
            if lines:
                section_header = lines[0][:100].strip()

            priority = PRIORITY_MAP.get(knowledge.get("risk", "info"), {"label": "Review", "color": "blue"})
            risk_reason = (
                f"Under {knowledge.get('statute', 'Indian Contract Act, 1872')}: "
                f"{knowledge.get('standard', 'Review required')} "
                f"[Market Standard: {knowledge.get('redline_hint', '')}]"
            )

            if clause_type == "Non-Compete" and "employment" in context.lower():
                risk_reason = (
                    f"CRITICAL — Section 27, Indian Contract Act, 1872. Post-employment non-compete clauses are "
                    f"void ab initio as they constitute a restraint of trade. Indian courts have "
                    f"consistently held (Niranjan Shankar Golikari v. Century Spinning, Percept D'Mark "
                    f"v. Zaheer Khan) that such clauses are unenforceable."
                )

            clauses.append({
                "clause_type": clause_type,
                "clause_text": context[:600],
                "section_header": section_header,
                "risk_level": knowledge.get("risk", "medium"),
                "risk_reason": risk_reason,
                "suggested_redline": knowledge.get("redline_hint", ""),
                "statute": knowledge.get("statute", "Indian Contract Act, 1872"),
                "priority": priority["label"],
                "market_standard": knowledge.get("standard", ""),
            })

    return clauses


def extract_clauses(contract_text: str, client: Optional[OpenAI] = None) -> list[dict]:
    if client is None:
        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    chunks = chunk_text(contract_text)
    all_clauses = []
    seen_in_current_chunk = set()

    for chunk in chunks:
        seen_in_current_chunk.clear()
        try:
            resp = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this contract under Indian law:\n\n{chunk}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=120,
            )
            content = resp.choices[0].message.content
            parsed = json.loads(content)
            raw_clauses = parsed if isinstance(parsed, list) else parsed.get("clauses", [parsed])
            for c in raw_clauses:
                if isinstance(c, dict) and c.get("clause_type") and c["clause_type"] not in seen_in_current_chunk:
                    seen_in_current_chunk.add(c["clause_type"])
                    ctype = c["clause_type"]
                    knowledge = CLAUSE_KNOWLEDGE_BASE.get(ctype)
                    if knowledge:
                        c["statute"] = knowledge["statute"]
                        c["priority"] = PRIORITY_MAP.get(knowledge["risk"], {"label": "Review"})["label"]
                        c["market_standard"] = knowledge["standard"]
                    all_clauses.append(c)
        except Exception:
            pass

    if not all_clauses:
        all_clauses = extract_with_keywords(contract_text)

    return all_clauses


def generate_compliance_report(text: str) -> list[dict]:
    text_lower = text.lower()
    results = []
    passed = 0
    for check in COMPLIANCE_CHECKS:
        keywords = COMPLIANCE_CHECK_KEYWORDS.get(check["name"], [])
        found = any(kw.lower() in text_lower for kw in keywords)
        if found:
            passed += 1
        results.append({
            "name": check["name"],
            "description": check["description"],
            "found": found,
            "status": "compliant" if found else "not_found",
            "icon": check["icon"],
        })
    return {
        "checks": results,
        "passed": passed,
        "total": len(COMPLIANCE_CHECKS),
        "score": round(passed / len(COMPLIANCE_CHECKS) * 100, 0) if COMPLIANCE_CHECKS else 0,
    }


def generate_summary(contract_text: str, client: Optional[OpenAI] = None) -> str:
    if client is None:
        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    chunks = chunk_text(contract_text, chunk_size=6000)
    if len(chunks) == 1:
        try:
            resp = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a legal document summarizer specializing in Indian contracts."},
                    {"role": "user", "content": chunks[0]},
                ],
                temperature=0.3,
                timeout=60,
            )
            return resp.choices[0].message.content
        except Exception:
            return "Summary generation failed."

    chunk_summaries = []
    for chunk in chunks:
        try:
            resp = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a legal document summarizer specializing in Indian contracts. Summarize this excerpt concisely."},
                    {"role": "user", "content": chunk},
                ],
                temperature=0.3,
                timeout=60,
            )
            chunk_summaries.append(resp.choices[0].message.content)
        except Exception:
            continue

    if not chunk_summaries:
        return "Summary generation failed."

    combined = "\n\n".join(chunk_summaries)
    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a legal document summarizer. Combine these excerpt summaries into one coherent overall summary of the contract."},
                {"role": "user", "content": combined},
            ],
            temperature=0.3,
            timeout=60,
        )
        return resp.choices[0].message.content
    except Exception:
        return combined[:2000]
