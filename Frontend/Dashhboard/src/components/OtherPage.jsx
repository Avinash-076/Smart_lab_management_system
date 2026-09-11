import Icon from "./Icon";

function OtherPage({
  active,
  setActive,
  navItems,
}) {
  const x = navItems.find(
    (n) => n[2] === active
  );

  return (
    <div className="other-page">
      <div className="other-card">
        <div className="other-icon">
          <Icon
            type={x?.[0] || "computer"}
            size={42}
          />
        </div>

        <h2>{x?.[1] || "Logout"}</h2>

        <p>
          This page is ready for the next module.
        </p>

        <button
          onClick={() =>
            setActive("computers")
          }
        >
          Back to Computer List
        </button>
      </div>
    </div>
  );
}

export default OtherPage;