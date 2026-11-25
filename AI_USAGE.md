# AI usage disclosure

AI assistance (ChatGPT) was used to help interpret the supplied assessment brief, structure the pytest suite, draft documentation, and identify contract-versus-implementation differences.

Independent verification performed:
- Read `API_CONTRACT.md` and compared each asserted behavior with the supplied `server.py`.
- Kept the supplied API fixture unchanged.
- Executed the suite against the local fixture and recorded the observed test outcomes in `TEST_REPORT.md`.
- Reviewed the test assertions to ensure the expected behavior comes from the assessment contract.

The author should review and understand every test and be prepared to explain the request helper, fixture isolation, parameterization, expected failures, and CI behavior during the technical interview.
