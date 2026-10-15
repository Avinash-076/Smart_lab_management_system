import Icon from "../../../../components/ui/Icon";
import { calculateComputerStats } from "../../utils/computerUtils";
import "./ComputerSummaryCards.css";

function ComputerSummaryCards({ computers = [] }) {
  const stats = calculateComputerStats(computers);

  return (
    <div className="computer-summary-cards" data-testid="computer-summary-cards">
      {/* 1. Total Computers */}
      <div className="summary-card" data-testid="card-total-computers">
        <div className="summary-card__icon-box summary-card__icon-box--blue">
          <Icon type="computer" size={24} />
        </div>
        <div className="summary-card__content">
          <span className="summary-card__label">Total Computers</span>
          <span className="summary-card__number">{stats.total}</span>
          <span className="summary-card__desc">All computers in lab</span>
        </div>
      </div>

      {/* 2. Online */}
      <div className="summary-card" data-testid="card-online">
        <div className="summary-card__icon-box summary-card__icon-box--green">
          <Icon type="pulse" size={24} />
        </div>
        <div className="summary-card__content">
          <span className="summary-card__label">Online</span>
          <span className="summary-card__number">{stats.online}</span>
          <span className="summary-card__desc">{stats.onlinePct}</span>
        </div>
      </div>

      {/* 3. Offline */}
      <div className="summary-card" data-testid="card-offline">
        <div className="summary-card__icon-box summary-card__icon-box--red">
          <Icon type="computer" size={24} />
        </div>
        <div className="summary-card__content">
          <span className="summary-card__label">Offline</span>
          <span className="summary-card__number">{stats.offline}</span>
          <span className="summary-card__desc">{stats.offlinePct}</span>
        </div>
      </div>

      {/* 4. Windows */}
      <div className="summary-card" data-testid="card-windows">
        <div className="summary-card__icon-box summary-card__icon-box--purple">
          <Icon type="windows" size={24} />
        </div>
        <div className="summary-card__content">
          <span className="summary-card__label">Windows</span>
          <span className="summary-card__number">{stats.windows}</span>
          <span className="summary-card__desc">{stats.windowsPct}</span>
        </div>
      </div>

      {/* 5. Other OS */}
      <div className="summary-card" data-testid="card-other-os">
        <div className="summary-card__icon-box summary-card__icon-box--amber">
          <Icon type="box" size={24} />
        </div>
        <div className="summary-card__content">
          <span className="summary-card__label">Other OS</span>
          <span className="summary-card__number">{stats.otherOS}</span>
          <span className="summary-card__desc">{stats.otherOSPct}</span>
        </div>
      </div>
    </div>
  );
}

export default ComputerSummaryCards;
