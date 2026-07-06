// Shared pagination helper for list endpoints.
//
// Reads ?limit= and ?offset= from the query object, clamps limit to
// [1, MAX_LIMIT], and returns a SQL fragment ( " LIMIT $n OFFSET $m" )
// while pushing the values onto the shared params array.
//
// Backward compatible: with no ?limit=, no LIMIT clause is produced and the
// full result set is returned exactly as before. An ?offset= without a
// ?limit= is honoured (valid in PostgreSQL).

const MAX_LIMIT = 500;

function buildPagination(query, params) {
  const lim = Number.parseInt(query.limit, 10);
  const off = Number.parseInt(query.offset, 10);
  let clause = '';
  if (Number.isInteger(lim) && lim > 0) {
    params.push(Math.min(lim, MAX_LIMIT));
    clause += ` LIMIT $${params.length}`;
  }
  if (Number.isInteger(off) && off > 0) {
    params.push(off);
    clause += ` OFFSET $${params.length}`;
  }
  return clause;
}

module.exports = { buildPagination, MAX_LIMIT };
