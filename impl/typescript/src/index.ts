/** Library entry point — the same functions the CLI uses, for embedding in another tool. */
export { Finding, codesOf, errors, warnings, frontMatter, loadConfig, loadCardFiles, expandGlob, collectCards } from "./core.js";
export type { Card, Config, Severity } from "./core.js";
export { validate, validateSchema, schemaPathFor, MATURITY } from "./validate.js";
export { CHECKS, checkRoutes, checkCoverage, checkMaturity, normalise, findCases, evidencePaths } from "./checks.js";
export type { CheckResult, TestCase } from "./checks.js";
export { runCardCorpus, runChecksCorpus } from "./conformance.js";
