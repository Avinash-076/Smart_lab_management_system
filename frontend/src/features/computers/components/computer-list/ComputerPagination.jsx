import { getPaginationItems } from "../../utils/computerUtils";
import "./ComputerPagination.css";

function ComputerPagination({
  page = 1,
  pages = 1,
  setPage,
  totalRows = 0,
  per = 8,
  setPer,
}) {
  const start = totalRows === 0 ? 0 : (page - 1) * per + 1;
  const end = Math.min(page * per, totalRows);
  const items = getPaginationItems(page, pages);

  return (
    <div className="computer-pagination" data-testid="computer-pagination">
      {/* 1. Results Summary */}
      <div className="computer-pagination__info">
        {`Showing ${start} to ${end} of ${totalRows} computers`}
      </div>

      {/* 2. Controls */}
      <div className="computer-pagination__controls">
        {/* First page button « */}
        <button
          type="button"
          className="computer-pagination__btn"
          disabled={page <= 1}
          onClick={() => setPage(1)}
          title="First page"
          aria-label="First page"
        >
          «
        </button>

        {/* Previous page button ‹ */}
        <button
          type="button"
          className="computer-pagination__btn"
          disabled={page <= 1}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          title="Previous page"
          aria-label="Previous page"
        >
          ‹
        </button>

        {/* Numbered Page Buttons & Ellipsis */}
        {items.map((item, idx) => {
          if (item === "...") {
            return (
              <span
                key={`ellipsis-${idx}`}
                className="computer-pagination__ellipsis"
                aria-hidden="true"
              >
                ...
              </span>
            );
          }

          const pageNum = Number(item);
          const isActive = page === pageNum;

          return (
            <button
              key={`page-${pageNum}`}
              type="button"
              className={`computer-pagination__btn ${isActive ? "active" : ""}`}
              onClick={() => setPage(pageNum)}
              aria-label={`Page ${pageNum}`}
              aria-current={isActive ? "page" : undefined}
            >
              {pageNum}
            </button>
          );
        })}

        {/* Next page button › */}
        <button
          type="button"
          className="computer-pagination__btn"
          disabled={page >= pages}
          onClick={() => setPage((p) => Math.min(pages, p + 1))}
          title="Next page"
          aria-label="Next page"
        >
          ›
        </button>

        {/* Last page button » */}
        <button
          type="button"
          className="computer-pagination__btn"
          disabled={page >= pages}
          onClick={() => setPage(pages)}
          title="Last page"
          aria-label="Last page"
        >
          »
        </button>

        {/* Page size dropdown */}
        {setPer && (
          <select
            className="computer-pagination__per-page"
            value={per}
            onChange={(e) => {
              setPer(Number(e.target.value));
              setPage(1);
            }}
            aria-label="Computers per page"
          >
            <option value={8}>8 / page</option>
            <option value={16}>16 / page</option>
            <option value={24}>24 / page</option>
            <option value={50}>50 / page</option>
          </select>
        )}
      </div>
    </div>
  );
}

export default ComputerPagination;
