# Eval questions: Juniper Hill Early Learning Center

Not loaded into the database. Check by hand against the chat (session locked to `juniper-hill`).

## Answerable (expected answer, source section)

| # | Question | Expected answer | Source |
|---|---|---|---|
| 1 | What time does the center open and close? | Opens 6:30 AM, closes 6:00 PM (pick-up deadline), Monday-Friday | `hours` |
| 2 | Are you open on weekends? | No, closed Saturday and Sunday | `hours` |
| 3 | What is the late pickup fee? | $2.00 per minute starting at 6:01 PM, no grace period | `policy:late_pickup`, `fees` |
| 4 | What happens if I'm late three times in a month? | Written notice from the Assistant Director | `policy:late_pickup` |
| 5 | How much is infant tuition? | $1,420 per month | `fees` |
| 6 | How much is Pre-K tuition, and are meals included? | $920 per month; meals and snacks are included | `fees`, `policy:lunch_info` |
| 7 | Is there a sibling discount? | Yes, 10% off the older child's tuition | `fees`, `policy:payments` |
| 8 | When is tuition due? | The 1st of the month; late after the 5th | `fees`, `policy:payments` |
| 9 | What is the registration fee? | $75, one-time and non-refundable | `fees` |
| 10 | Who is the center nurse and how do I reach them? | Rosalind Vega, RN, (505) 555-0124, nurse@juniperhill.test | `contacts` |
| 11 | What fever means my child must stay home? | 100.4 F (38.0 C) or higher | `policy:illness_exclusion` |
| 12 | When can my child come back after a fever? | After 24 hours fever-free without fever-reducing medicine | `policy:illness_exclusion` |
| 13 | Is the center closed for Thanksgiving? | Yes, Wed 11/25 to Fri 11/27/2026 | `closures` |
| 14 | When is winter break? | Closed 12/21/2026 through 1/1/2027; reopens 1/4/2027 | `closures` |
| 15 | What's for lunch on Tuesday? | Baked chicken drumstick, brown rice, roasted carrots; milk | `lunch_menu` |
| 16 | Can I bring homemade cupcakes for my child's birthday? | No. Only store-bought, nut-free, sealed treats with labels, 48 hours' notice | `policy:birthdays` |
| 17 | What documents do I need to enroll? | Enrollment form, proof of age, immunization record, physical within 12 months, allergy plans, pick-up form (income proof for assistance) | `policy:enrollment` |
| 18 | When does nap time start for toddlers? | 11:45 AM to 2:15 PM | `schedule` |
| 19 | Can my child bring a toy from home? | No toys from home; one soft comfort item for rest time is allowed | `policy:items_from_home` |
| 20 | Who is the director? | Marguerite Alvarado, (505) 555-0121, director@juniperhill.test | `contacts` |
| 21 | When is the early release on Fridays? | Last Friday of each month the center closes at 3:00 PM | `hours` |

## Not answerable (expected: say it isn't in the information, give (505) 555-0120 and office@juniperhill.test)

| # | Question | Notes |
|---|---|---|
| N1 | Do you offer a summer camp? | No info in the data |
| N2 | Is there a bus or transportation service? | No info |
| N3 | What is your field trip policy? | No info |
| N4 | Do you teach Spanish or have a bilingual program? | No info |
| N5 | What are Little Comets' hours? (other center) | Must not use any other center's data |

## Follow-up pairs

| # | Question | Follow-up | Expected |
|---|---|---|---|
| F1 | What's the late pickup fee? | And what time does it start? | $2/minute; starts at 6:01 PM |
| F2 | How much is toddler tuition? | What about for two kids? | $1,240/month; 10% off the older child's tuition. Needs conversation context |
| F3 | When is the center closed in November? | And what about December? | Veterans Day 11/11, Thanksgiving break 11/25-27; December: winter break from 12/21 |

## Spanish

| # | Question | Expected |
|---|---|---|
| S1 | A que hora cierra el centro? | Answer in Spanish: 6:00 PM (abre a las 6:30 AM) |
| S2 | Cuanto cuesta la matricula de bebes? | Answer in Spanish: $1,420 al mes; registration $75 |
