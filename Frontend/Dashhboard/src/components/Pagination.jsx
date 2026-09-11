function Pagination({
  page,
  pages,
  setPage,
  rows,
  totalRows,
  per,
}) {
  const start =
    totalRows === 0 ? 0 : (page - 1) * per + 1;

  const end = Math.min(
    page * per,
    totalRows
  );

  return (
    <div className="pagination">
      <div className="pagination-info">
        Showing {start}–{end} of {totalRows} computers
      </div>

      <div className="pagination-buttons">
        <button
          disabled={page === 1}
          onClick={() =>
            setPage((p) => Math.max(1, p - 1))
          }
        >
          Previous
        </button>

        {Array.from(
          { length: pages },
          (_, i) => i + 1
        ).map((number) => (
          <button
            key={number}
            className={
              page === number ? "active" : ""
            }
            onClick={() => setPage(number)}
          >
            {number}
          </button>
        ))}

        <button
          disabled={page === pages}
          onClick={() =>
            setPage((p) =>
              Math.min(pages, p + 1)
            )
          }
        >
          Next
        </button>
      </div>
    </div>
  );
}

export default Pagination;