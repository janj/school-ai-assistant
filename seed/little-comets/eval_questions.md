# Eval questions: Little Comets Preschool

Not loaded into the database. Check by hand against the chat (session locked to `little-comets`).

## Answerable (expected answer, source section)

| # | Question | Expected answer | Source |
|---|---|---|---|
| 1 | What are your hours? | 7:30 AM to 5:30 PM Monday-Friday; programs run 8:30-12:30 (part-day) or 8:30-3:30 (full-day) | `hours` |
| 2 | Do you close early on any day? | Wednesdays at 3:30 PM | `hours` |
| 3 | What is the late pickup fee? | $15 per 15-minute block after a 10-minute grace period | `policy:late_pickup`, `fees` |
| 4 | I'm 20 minutes past my pickup time. What do I owe? | $15 (one block; grace period is 10 minutes) | `policy:late_pickup` |
| 5 | How much is full-day tuition for 5 days? | $285 per week | `fees` |
| 6 | How much is part-day for 3 days? | $110 per week | `fees` |
| 7 | Is there a sibling discount? | Yes, $10 per week off per additional child | `fees`, `policy:payments` |
| 8 | When do I pay tuition? | Every Friday for the following week, via the parent portal | `fees`, `policy:payments` |
| 9 | What's the registration fee? | $50, one-time, non-refundable | `fees` |
| 10 | Do you provide lunch? | No; families pack lunch for full-day children. The center provides a 9:30 AM snack | `policy:lunch_info`, `lunch_menu` |
| 11 | What's the snack on Wednesday? | Cucumber sticks with ranch dip and pretzels; water | `lunch_menu` |
| 12 | Can I send peanut butter sandwiches? | No, the center is nut-free; sunflower seed butter is fine | `policy:lunch_info` |
| 13 | What temperature counts as a fever? | 100.0 F (37.8 C) or higher | `policy:illness_exclusion` |
| 14 | How long after vomiting must my child stay home? | Symptom-free for 48 hours | `policy:illness_exclusion` |
| 15 | When is spring break? | March 22 to 26, 2027 | `closures` |
| 16 | When is the last day of school? | June 4, 2027; closed for the summer after | `closures` |
| 17 | How old must my child be to enroll? | 2 years old by September 1, up to age 5 | `policy:enrollment` |
| 18 | How do I join the waitlist? | Email enroll@littlecomets.test with child's birth date and preferred schedule; no fee | `policy:enrollment` |
| 19 | Can we bring birthday treats? | Optional; store-bought and nut-free, one week's notice | `policy:birthdays` |
| 20 | Who runs the center? | Nadia Castellanos, (505) 555-0161, nadia@littlecomets.test | `contacts` |
| 21 | What time is rest time in the Star Room? | 1:00 to 2:00 PM | `schedule` |

## Not answerable (expected: say it isn't in the information, give (505) 555-0160 and hello@littlecomets.test)

| # | Question | Notes |
|---|---|---|
| N1 | Do you have a summer camp? | Closes after June 4; no summer info |
| N2 | Do you offer a bus or transportation? | No info |
| N3 | What is your field trip policy? | No info |
| N4 | Do you accept infants? | Data only covers ages 2-5; say that ages 2-5 are served, and no infant program is described |
| N5 | What is Juniper Hill's late fee? (other center) | Must not use any other center's data |

## Follow-up pairs

| # | Question | Follow-up | Expected |
|---|---|---|---|
| F1 | What's the late pickup fee? | And after 5:40 PM? | $15 per 15-minute block; 5:40 PM is when grace ends for extended care |
| F2 | How much is full-day tuition? | And part-day? | $285/week for 5 days full-day; $165/week for 5 days part-day |
| F3 | When is the center closed in December? | What about in January? | Winter break from 12/23; reopens 1/4/2027; MLK Day 1/18 |

## Spanish

| # | Question | Expected |
|---|---|---|
| S1 | A que hora termina el programa de dia completo? | Answer in Spanish: 3:30 PM |
| S2 | Hay que llevar almuerzo? | Answer in Spanish: yes, families pack lunch for full-day; the center gives a snack |
