import Icon from "./Icon";

function StatCard({
  icon,
  title,
  number,
  footer,
  type,
}) {
  return (
    <div className="card">
      <div className={`card-icon ${type}`}>
        <Icon type={icon} size={29} />
      </div>

      <div>
        <div className="card-title">
          {title}
        </div>

        <div className={`card-number ${type}`}>
          {number}
        </div>

        <div className="card-footer">
          {footer}
        </div>
      </div>
    </div>
  );
}

export default StatCard;