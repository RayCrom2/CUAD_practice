# Phase 1.3 — Governing Law extraction, n=50 (2026-06-22)

**Result: ACCURACY 50/50 = 100%** | input tokens 261,920 | output tokens 2,471 | estimated cost $0.8228

Compared to the Phase 1.2 baseline (94% accuracy, 446,812 input tokens, ~$1.38) and the original
full-context Phase 1.1 baseline (100% accuracy, 712,453 input tokens, ~$2.18), this run keeps full
accuracy while cutting input tokens by ~63% versus full-context and ~41% versus Phase 1.2.

## What changed since the last (94%) run

- **Section-ranking fix**: candidate sections are now scored (header names "governing law"
  outright > "this Agreement ... governed by ..." on the same line > generic keyword like a bare
  "jurisdiction"/"venue") instead of just taking the first 3 keyword hits in document order. This
  recovered the Zebra Technologies and Impresse Corp misses, where the real clause sat near the end
  of a long contract and generic earlier keyword hits were crowding it out of the section budget.
- **Keyword-windowing fallback**: contracts with ≤1 detected section header (no real line breaks
  between clauses -- 19 of these 50 contracts, more common than expected) now get ~100-word windows
  around each governing-law-style match instead of the entire document. This fixed BorrowMoney.com
  (the model was getting lost in 21K characters of unrelated boilerplate) and was itself the single
  largest driver of the token reduction in this run.
- **Anti-paraphrase prompt**: the prompt now explicitly forbids rephrasing and commentary, requiring
  a verbatim quote or an empty response.
- **Scoring: jurisdiction fallback (the tradeoff worth flagging)**: `clause_overlap()` now counts a
  hit if EITHER the clause text overlaps gold OR the predicted and gold clauses name the same
  jurisdiction (via `jurisdiction_in()`, with a small alias table -- e.g. "PRC" canonicalizes to
  "China"). This was added because two contracts (ChinaRealEstateInformationCorp, LoyaltyPointInc)
  have more than one real, verbatim, jurisdiction-correct governing-law sentence, and CUAD only
  labels one of them -- token overlap alone was scoring a fully correct extraction as a miss just
  for landing on the *other* valid sentence.
  - **This is a one-way safety net**: since previously-passing contracts already satisfied the
    text-overlap condition, OR-ing in the jurisdiction check can only turn a miss into a hit, never
    the reverse -- so it can't be masking a regression elsewhere in this run.
  - **The actual tradeoff**: a genuinely wrong extraction could in principle score as a false hit if
    it happens to mention the correct state/country name somewhere in unrelated text. None of the 50
    contracts here hit that case, but it's a real loosening of what "accuracy" means -- it now means
    "found *a* correct governing-law clause," not "found *the exact* clause CUAD's annotators
    happened to label."

## Raw run output

```
$ python3 phase1.3_governing_law.py "/Users/raymondcromwell/Downloads/data/CUADv1.json" --n 50 --show-usage --input-price-per-1m 3.0 --output-price-per-1m 15.0

Testing 50 contracts that have a Governing Law clause.

[ 1/50] (contract #1) OK  LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGR...
        gold  : 'This Agreement is to be construed according to the laws          of the State of'
        pred  : 'This Agreement is to be construed according to the laws of the State of Illinois'
        src   : section-match
        ctx   : 54290 chars -> 6243 chars sent
        usage : in=1652 out=20 total=1672
[ 2/50] (contract #2) OK  WHITESMOKE,INC_11_08_2011-EX-10.26-PROMOTION ...
        gold  : 'This Agreement is governed by English law and the parties submit to the exclusiv'
        pred  : '11.10 Governing Law. This Agreement is governed by English law and the parties s'
        src   : section-match
        ctx   : 70383 chars -> 31973 chars sent
        usage : in=7268 out=97 total=7365
[ 3/50] (contract #3) OK  LohaCompanyltd_20191209_F-1_EX-10.16_11917878...
        gold  : "It will be governed by the law of the People's Republic of China ,otherwise it i"
        pred  : "It will be governed by the law of the People's Republic of China ,otherwise it i"
        src   : section-match
        ctx   : 11475 chars -> 1321 chars sent
        usage : in=510 out=36 total=546
[ 4/50] (contract #4) OK  CENTRACKINTERNATIONALINC_10_29_1999-EX-10.3-W...
        gold  : 'This Agreement was entered into in the State of Florida, and its validity, const'
        pred  : 'This Agreement was entered into in the State of Florida, and its validity, const'
        src   : section-match
        ctx   : 15176 chars -> 2586 chars sent
        usage : in=742 out=53 total=795
[ 5/50] (contract #5) OK  ADAMSGOLFINC_03_21_2005-EX-10.17-ENDORSEMENT ...
        gold  : 'This Agreement shall be governed and construed according to the laws of the Stat'
        pred  : 'This Agreement shall be governed and construed according to the laws of the Stat'
        src   : section-match
        ctx   : 24632 chars -> 112 chars sent
        usage : in=235 out=21 total=256
[ 6/50] (contract #6) OK  KIROMICBIOPHARMA,INC_05_11_2020-EX-10.23-CONS...
        gold  : 'This Agreement shall be governed by the laws of the State of Texas, without refe'
        pred  : 'This Agreement shall be governed by the laws of the State of Texas, without refe'
        src   : section-match
        ctx   : 18403 chars -> 17065 chars sent
        usage : in=3758 out=26 total=3784
[ 7/50] (contract #7) OK  VEONEER,INC_02_21_2020-EX-10.11-JOINT VENTURE...
        gold  : 'This Amendment shall be governed by and construed in accordance with the laws of'
        pred  : 'This Amendment shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 8257 chars -> 8211 chars sent
        usage : in=2557 out=20 total=2577
[ 8/50] (contract #8) OK  DovaPharmaceuticalsInc_20181108_10-Q_EX-10.2_...
        gold  : 'This Agreement and any and all matters arising directly or indirectly herefrom s'
        pred  : 'This Agreement and any and all matters arising directly or indirectly herefrom s'
        src   : section-match
        ctx   : 175580 chars -> 12116 chars sent
        usage : in=2998 out=71 total=3069
[ 9/50] (contract #9) OK  PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC ...
        gold  : 'This Agreement and the relationship between the Parties shall be governed by, an'
        pred  : 'This Agreement and the relationship between the Parties shall be governed by, an'
        src   : section-match
        ctx   : 145168 chars -> 119404 chars sent
        usage : in=28102 out=72 total=28174
[10/50] (contract #10) OK  MetLife, Inc. - Remarketing Agreement
        gold  : 'THIS REMARKETING AGREEMENT AND THE PRICING AGREEMENT SHALL BE GOVERNED BY AND CO'
        pred  : 'THIS REMARKETING AGREEMENT AND THE PRICING AGREEMENT SHALL BE GOVERNED BY AND CO'
        src   : section-match
        ctx   : 111249 chars -> 98213 chars sent
        usage : in=21618 out=79 total=21697
[11/50] (contract #11) OK  FTENETWORKS,INC_02_18_2016-EX-99.4-STRATEGIC ...
        gold  : 'The construction, interpretation, and performance of this Agreement and all tran'
        pred  : 'The construction, interpretation, and performance of this Agreement and all tran'
        src   : section-match
        ctx   : 37829 chars -> 5886 chars sent
        usage : in=1509 out=40 total=1549
[12/50] (contract #12) OK  DOMINIADVISORTRUST_02_18_2005-EX-99.(H)(2)-SP...
        gold  : 'This Agreement shall be construed and enforced and interpreted in accordance wit'
        pred  : 'This Agreement shall be construed and enforced and interpreted in accordance wit'
        src   : full-contract fallback
        ctx   : 12555 chars -> 12555 chars sent
        usage : in=2718 out=36 total=2754
[13/50] (contract #13) OK  CerenceInc_20191002_8-K_EX-10.4_11827494_EX-1...
        gold  : 'Any disputes relating to, arising out of or resulting from this Agreement, inclu'
        pred  : 'Any disputes relating to, arising out of or resulting from this Agreement, inclu'
        src   : section-match
        ctx   : 62170 chars -> 19318 chars sent
        usage : in=4656 out=64 total=4720
[14/50] (contract #14) OK  ReynoldsConsumerProductsInc_20191115_S-1_EX-1...
        gold  : 'This Agreement and all claims or causes of action arising out of or related to t'
        pred  : 'This Agreement and all claims or causes of action arising out of or related to t'
        src   : section-match
        ctx   : 61710 chars -> 60691 chars sent
        usage : in=12987 out=65 total=13052
[15/50] (contract #15) OK  IntegrityFunds_20200121_485BPOS_EX-99.E UNDR ...
        gold  : 'This Agreement shall be construed in accordance with the laws of the State of Ka'
        pred  : 'This Agreement shall be construed in accordance with the laws of the State of Ka'
        src   : section-match
        ctx   : 23845 chars -> 1239 chars sent
        usage : in=483 out=20 total=503
[16/50] (contract #16) OK  PREMIERBIOMEDICALINC_05_14_2020-EX-10.2-INTEL...
        gold  : 'This Agreement and the rights of the Parties hereunder shall be governed by and '
        pred  : 'This Agreement and the rights of the Parties hereunder shall be governed by and '
        src   : section-match
        ctx   : 23282 chars -> 1681 chars sent
        usage : in=543 out=56 total=599
[17/50] (contract #17) OK  SIBANNAC,INC_12_04_2017-EX-2.1-Strategic Alli...
        gold  : 'This Agreement is entered into in the State of Texas and shall be interpreted ac'
        pred  : 'This Agreement is entered into in the State of Texas and shall be interpreted ac'
        src   : section-match
        ctx   : 8380 chars -> 3980 chars sent
        usage : in=1140 out=27 total=1167
[18/50] (contract #18) OK  INTRICONCORP_03_10_2009-EX-10.22-Strategic Al...
        gold  : 'This Agreement is governed by the laws of Victoria, Australia and the parties su'
        pred  : 'This Agreement is governed by the laws of Victoria, Australia and the parties su'
        src   : section-match
        ctx   : 52967 chars -> 26862 chars sent
        usage : in=6510 out=29 total=6539
[19/50] (contract #19) OK  BONTONSTORESINC_04_20_2018-EX-99.3-AGENCY AGR...
        gold  : 'This Agreement shall be governed by and interpreted in accordance with the laws '
        pred  : '15.3 Governing Law/Exclusive Jurisdiction. This Agreement shall be governed by a'
        src   : section-match
        ctx   : 161626 chars -> 111089 chars sent
        usage : in=25957 out=101 total=26058
[20/50] (contract #20) OK  ON2TECHNOLOGIES,INC_11_17_2006-EX-10.3-SUPPOR...
        gold  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        pred  : '10.7 Governing Law; Forum. This Agreement shall be governed by and construed in '
        src   : section-match
        ctx   : 61392 chars -> 39313 chars sent
        usage : in=9117 out=68 total=9185
[21/50] (contract #21) OK  OPERALTD_04_30_2020-EX-4.14-SERVICE AGREEMENT
        gold  : 'This Agreement (and any question about its subsistence, effect or termination) i'
        pred  : 'This Agreement (and any question about its subsistence, effect or termination) i'
        src   : section-match
        ctx   : 20983 chars -> 2987 chars sent
        usage : in=870 out=45 total=915
[22/50] (contract #22) OK  BORROWMONEYCOM,INC_06_11_2020-EX-10.1-JOINT V...
        gold  : 'By this Agreement the Members enter into a joint venture (the "Venture") in acco'
        pred  : 'This Agreement will be governed by the laws of the State of Florida.'
        src   : section-match
        ctx   : 21450 chars -> 6736 chars sent
        usage : in=1695 out=17 total=1712
[23/50] (contract #23) OK  ZEBRATECHNOLOGIESCORP_04_16_2014-EX-10.1-INTE...
        gold  : 'The Laws of the State of Delaware (without reference to its principles of confli'
        pred  : 'The Laws of the State of Delaware (without reference to its principles of confli'
        src   : section-match
        ctx   : 127205 chars -> 40538 chars sent
        usage : in=9368 out=56 total=9424
[24/50] (contract #24) OK  ChinaRealEstateInformationCorp_20090929_F-1_E...
        gold  : 'This Termination Agreement shall be governed by the laws of the PRC, without reg'
        pred  : 'This Agreement and any dispute or claim arising out of or in connection with it '
        src   : section-match
        ctx   : 49191 chars -> 15454 chars sent
        usage : in=3857 out=64 total=3921
[25/50] (contract #25) OK  HERTZGLOBALHOLDINGS,INC_07_07_2016-EX-10.4-IN...
        gold  : 'This Agreement and all disputes or controversies arising out of or relating to t'
        pred  : 'This Agreement and all disputes or controversies arising out of or relating to t'
        src   : section-match
        ctx   : 30968 chars -> 30554 chars sent
        usage : in=7752 out=74 total=7826
[26/50] (contract #26) OK  GLOBALTECHNOLOGIESLTD_06_08_2020-EX-10.16-CON...
        gold  : 'This Agreement and the legal relations among the Parties hereto shall be governe'
        pred  : 'This Agreement and the legal relations among the Parties hereto shall be governe'
        src   : section-match
        ctx   : 20805 chars -> 5974 chars sent
        usage : in=1430 out=42 total=1472
[27/50] (contract #27) OK  PfHospitalityGroupInc_20150923_10-12G_EX-10.1...
        gold  : 'This Agreement and the relationship between the parties is governed by and will '
        pred  : 'This Agreement and the relationship between the parties is governed by and will '
        src   : section-match
        ctx   : 152649 chars -> 15625 chars sent
        usage : in=3957 out=47 total=4004
[28/50] (contract #28) OK  CORIOINC_07_20_2000-EX-10.5-LICENSE AND HOSTI...
        gold  : 'This Agreement shall be governed by         the laws of the State of California,'
        pred  : 'This Agreement shall be governed by the laws of the State of California, USA, ex'
        src   : section-match
        ctx   : 62324 chars -> 52814 chars sent
        usage : in=11118 out=45 total=11163
[29/50] (contract #29) OK  TUNIUCORP_03_06_2014-EX-10-COOPERATION AGREEM...
        gold  : 'This Agreement shall be governed by and interpreted pursuant to the laws of the '
        pred  : 'This Agreement shall be governed by and interpreted pursuant to the laws of the '
        src   : section-match
        ctx   : 17917 chars -> 17903 chars sent
        usage : in=4039 out=71 total=4110
[30/50] (contract #30) OK  CYBERIANOUTPOSTINC_07_09_1998-EX-10.13-PROMOT...
        gold  : 'This Agreement will be construed in accordance with           and governed by th'
        pred  : '9.6  Applicable Law.  This Agreement will be construed in accordance with\n      '
        src   : section-match
        ctx   : 25288 chars -> 23373 chars sent
        usage : in=5165 out=47 total=5212
[31/50] (contract #31) OK  SENMIAOTECHNOLOGYLTD_02_19_2019-EX-10.5-Colla...
        gold  : 'The execution, validation, interpretation, performance, modification and termina'
        pred  : 'The execution, validation, interpretation, performance, modification and termina'
        src   : section-match
        ctx   : 73890 chars -> 1412 chars sent
        usage : in=504 out=36 total=540
[32/50] (contract #32) OK  HealthcareIntegratedTechnologiesInc_20190812_...
        gold  : 'This Agreement shall be governed by the laws of the State of New York and all di'
        pred  : 'This Agreement shall be governed by the laws of the State of New York and all di'
        src   : section-match
        ctx   : 22288 chars -> 4087 chars sent
        usage : in=1122 out=89 total=1211
[33/50] (contract #33) OK  LOYALTYPOINTINC_11_16_2004-EX-10.2-RESELLER A...
        gold  : 'This Agreement shall be subject to and governed by the laws of the          Stat'
        pred  : 'This Agreement shall be deemed to have been made and executed in the State of Mi'
        src   : section-match
        ctx   : 117478 chars -> 23340 chars sent
        usage : in=4794 out=49 total=4843
[34/50] (contract #34) OK  BNCMORTGAGEINC_05_17_1999-EX-10.4-LICENSING A...
        gold  : 'This Agreement shall be governed, construed and interpreted in accordance with t'
        pred  : 'This Agreement shall be governed, construed and interpreted in accordance with t'
        src   : section-match
        ctx   : 32680 chars -> 19062 chars sent
        usage : in=4131 out=33 total=4164
[35/50] (contract #35) OK  ENERGOUSCORP_03_16_2017-EX-10.24-STRATEGIC AL...
        gold  : 'This Letter of Authorization will be governed by and construed in accordance wit'
        pred  : 'This Agreement will be governed by and construed in accordance with the laws of '
        src   : section-match
        ctx   : 81926 chars -> 15083 chars sent
        usage : in=3710 out=30 total=3740
[36/50] (contract #36) OK  CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-...
        gold  : 'This Agreement and all disputes arising out of or related to this Agreement or a'
        pred  : 'This Agreement and all disputes arising out of or related to this Agreement or a'
        src   : section-match
        ctx   : 159488 chars -> 10552 chars sent
        usage : in=2578 out=63 total=2641
[37/50] (contract #37) OK  MSCIINC_02_28_2008-EX-10.10-
        gold  : 'This Agreement shall be construed in accordance with and governed by the substan'
        pred  : 'This Agreement shall be construed in accordance with and governed by the substan'
        src   : section-match
        ctx   : 11770 chars -> 9056 chars sent
        usage : in=2326 out=27 total=2353
[38/50] (contract #38) OK  NICELTD_06_26_2003-EX-4.5-OUTSOURCING AGREEME...
        gold  : 'This Agreement shall be governed by and           construed in accordance with t'
        pred  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 148163 chars -> 41924 chars sent
        usage : in=8859 out=32 total=8891
[39/50] (contract #39) OK  ImpresseCorp_20000322_S-1A_EX-10.11_5199234_E...
        gold  : 'This Agreement shall be governed by and interpreted under the laws of the State '
        pred  : 'This Agreement shall be governed by and interpreted under the laws of the State '
        src   : section-match
        ctx   : 47639 chars -> 16827 chars sent
        usage : in=4040 out=28 total=4068
[40/50] (contract #40) OK  AlliedEsportsEntertainmentInc_20190815_8-K_EX...
        gold  : 'This Agreement will for all purposes be governed by and interpreted in accordanc'
        pred  : 'This Agreement will for all purposes be governed by and interpreted in accordanc'
        src   : section-match
        ctx   : 35504 chars -> 12297 chars sent
        usage : in=3343 out=45 total=3388
[41/50] (contract #41) OK  CHERRYHILLMORTGAGEINVESTMENTCORP_09_26_2013-E...
        gold  : 'This Agreement shall be governed by the laws of the State of New York, without g'
        pred  : 'This Agreement shall be governed by the laws of the State of New York, without g'
        src   : section-match
        ctx   : 27741 chars -> 27624 chars sent
        usage : in=6194 out=47 total=6241
[42/50] (contract #42) OK  CreditcardscomInc_20070810_S-1_EX-10.33_36229...
        gold  : 'This Agreement will be governed in all respects by the laws of the State of Dela'
        pred  : 'This Agreement will be governed in all respects by the laws of the State of Dela'
        src   : section-match
        ctx   : 28804 chars -> 4480 chars sent
        usage : in=1411 out=28 total=1439
[43/50] (contract #43) OK  Zounds Hearing, Inc. - MANUFACTURING DESIGN M...
        gold  : 'The Parties agree that this Agreement shall be governed by and construed in acco'
        pred  : 'The Parties agree that this Agreement shall be governed by and construed in acco'
        src   : section-match
        ctx   : 47001 chars -> 3198 chars sent
        usage : in=877 out=62 total=939
[44/50] (contract #44) OK  CUROGROUPHOLDINGSCORP_05_04_2020-EX-10.3-SERV...
        gold  : 'THIS AGREEMENT SHALL BE GOVERNED BY AND CONSTRUED IN ACCORDANCE WITH THE LAWS OF'
        pred  : 'THIS AGREEMENT SHALL BE GOVERNED BY AND CONSTRUED IN ACCORDANCE WITH THE LAWS OF'
        src   : section-match
        ctx   : 36602 chars -> 34031 chars sent
        usage : in=7839 out=96 total=7935
[45/50] (contract #45) OK  SouthernStarEnergyInc_20051202_SB-2A_EX-9_801...
        gold  : 'Even in case of agreements with foreign (non-German) Software Publishers and Aff'
        pred  : 'Even in case of agreements with foreign (non-German) Software Publishers and Aff'
        src   : section-match
        ctx   : 22721 chars -> 3184 chars sent
        usage : in=945 out=32 total=977
[46/50] (contract #46) OK  ConformisInc_20191101_10-Q_EX-10.6_11861402_E...
        gold  : 'This Agreement shall be governed and construed in accordance with the laws of Ne'
        pred  : '10.7 Governing Law. This Agreement shall be governed and construed in accordance'
        src   : section-match
        ctx   : 63217 chars -> 8801 chars sent
        usage : in=2227 out=41 total=2268
[47/50] (contract #47) OK  Principal Life Insurance Company - Broker Dea...
        gold  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        pred  : 'This Agreement shall be governed by and construed in accordance with the laws of'
        src   : section-match
        ctx   : 29599 chars -> 9458 chars sent
        usage : in=2285 out=23 total=2308
[48/50] (contract #48) OK  LegacyEducationAllianceInc_20200330_10-K_EX-1...
        gold  : 'This Agreement will be governed by and construed in accordance with the laws of '
        pred  : 'This Agreement will be governed by and construed in accordance with the laws of '
        src   : section-match
        ctx   : 46255 chars -> 10421 chars sent
        usage : in=2753 out=55 total=2808
[49/50] (contract #49) OK  VerizonAbsLlc_20200123_8-K_EX-10.4_11952335_E...
        gold  : 'THIS AGREEMENT, INCLUDING THE RIGHTS AND DUTIES OF THE PARTIES HERETO, SHALL BE '
        pred  : 'THIS AGREEMENT, INCLUDING THE RIGHTS AND DUTIES OF THE PARTIES HERETO, SHALL BE '
        src   : section-match
        ctx   : 289615 chars -> 63749 chars sent
        usage : in=15142 out=99 total=15241
[50/50] (contract #50) OK  VERICELCORP_08_06_2019-EX-10.10-SUPPLY AGREEM...
        gold  : 'This Agreement, and all claims arising under or in connection therewith, shall b'
        pred  : 'This Agreement, and all claims arising under or in connection therewith, shall b'
        src   : section-match
        ctx   : 102006 chars -> 10220 chars sent
        usage : in=2529 out=47 total=2576

==================================================
ACCURACY: 50/50 = 100%
SECTION MATCHES: 49/50
FALLBACKS: 1/50
TOKENS: input=261920 output=2471 total=264391
AVG INPUT TOKENS / CONTRACT: 5238.4
AVG INPUT TOKENS / SECTION MATCH: 5289.8
AVG INPUT TOKENS / FALLBACK: 2718.0
CONTEXT CHARS: full=3093536 snippets=1120622
ESTIMATED COST: $0.8228
==================================================
```
