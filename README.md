DARA - DEVELOPMENT OF A DIALECT-AWARE DIGITAL REPOSITORY AND API
FOR INDIGENOUS NIGERIAN LANGUAGES

Department of Mathematical and Computer Sciences
College of Natural and Applied Sciences
Fountain University, Osogbo
Supervisor: Dr. (Mrs) M. A. Ogunrinde
July 2026

SUBMITTED BY
  BELLO, Jamiu Muhammad            FUO220218
  BABALOLA, Hamid Taiwo            FUO220219
  OYEKOLA, AbdulSalam Obajuwon     FUO230403

------------------------------------------------------------------
CONTENTS OF THIS SUBMISSION
------------------------------------------------------------------

01_Project_Report
    DARA_Project_Report_FINAL.docx    Complete report (Word)
    DARA_Project_Report_FINAL.pdf     Complete report (PDF)
    DARA_Certification_Signed.pdf     Signed certification page

02_Project_Summary
    DARA_Project_Summary_15pg.docx    15-page summary (Word)
    DARA_Project_Summary_15pg.pdf     15-page summary (PDF)

03_Source_Code
    src/                Node.js and Express REST API
    scripts/seed/       Python data seeding pipeline and tests
    clean/              Cleaned source datasets
    docs/               Design specifications
    package.json        Node dependencies
    requirements.txt    Python dependencies
    .env.example        Environment variable template
    README.md           Repository documentation

04_Installation_Guide
    DARA_Installation_Guide.docx / .pdf

05_User_Manual
    DARA_User_Manual.docx / .pdf
    Contains the hosting link and access credentials.

------------------------------------------------------------------
QUICK ACCESS
------------------------------------------------------------------

Live API documentation   https://dara-ze5e.onrender.com/api-docs
Live API base URL        https://dara-ze5e.onrender.com/api
Source repository        https://github.com/shinigamieaper/DARA

ACCESS MODEL
  Read access    Open. No login required for any GET endpoint.
  Write access   Requires the API key in the x-api-key header.
                 Key: dialect2026

  DARA is a programmatic API, not a website with user accounts,
  so there are no usernames or passwords. Full detail is in the
  User Manual, section 3.

NOTE ON HOSTING
  The service runs on free-tier hosting and suspends when idle.
  The first request after a period of inactivity can take up to
  a minute to respond while the service restarts.

NO APK IS INCLUDED
  DARA is a REST API and database, not a mobile application, so
  requirement 6 does not apply to this project.
