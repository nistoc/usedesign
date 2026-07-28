// Fixture — illustrative source, not a running service.
//
// It exists to show where the entries in ../route-inventory.json come from, and
// in particular that half of them are not written anywhere in this file.

import { Router } from 'express'

export const router = Router()   // mounted by the app at /v1

// --- registered individually -------------------------------------------------
// These three can be found by grepping, and a marker comment could be placed
// above each one.

router.post('/copies/:copyId/checkout', checkout)
router.post('/imports', startImport)
router.get('/members/:memberId/settlement', settlement)

// --- registered from a template ----------------------------------------------
// Four routes are born here. There is no line to put a marker on, and a parser
// that does not interpret this loop sees two registrations instead of four.
//
// This is the ordinary shape of admin CRUD, not a contrived case: one real
// system measured ~180 routes against ~90-110 operations, and the difference
// was expansion exactly like this.

for (const resource of ['members', 'api-keys']) {
  router.post(`/admin/${resource}`, adminCreate(resource))
  router.delete(`/admin/${resource}/:id`, adminDelete(resource))
}

// --- infrastructure ----------------------------------------------------------
// Served, but not operations. See usedesign.config.yaml.

router.get('/health', liveness)
router.get('/metrics', metrics)
router.get('/docs', docsUi)
router.get('/docs/openapi.json', openapiDocument)
