import { css } from "lit";

/** Styles shared by all views; colours come from the Home Assistant theme. */
export const sharedStyles = css`
  :host {
    display: block;
  }
  ha-card {
    display: block;
    margin-bottom: 16px;
  }
  .card-content {
    padding: 0 16px 16px;
  }
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 16px 16px 8px;
    font-size: 20px;
    font-weight: 500;
    color: var(--primary-text-color);
  }
  .card-subtitle {
    margin: -4px 16px 12px;
    color: var(--secondary-text-color);
    font-size: 14px;
    line-height: 1.4;
  }
  .card-actions {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    padding: 8px 16px;
    border-top: 1px solid var(--divider-color);
  }
  .card-actions .spacer {
    flex: 1;
  }
  .section-title {
    margin: 24px 0 4px;
    font-size: 15px;
    font-weight: 500;
    color: var(--primary-text-color);
  }
  .section-title:first-child {
    margin-top: 8px;
  }
  .muted {
    color: var(--secondary-text-color);
  }
  .code {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 36px;
    height: 36px;
    padding: 0 8px;
    box-sizing: border-box;
    border-radius: 10px;
    background: rgba(var(--rgb-primary-color), 0.14);
    color: var(--primary-color);
    font-weight: 600;
    font-size: 16px;
    font-family: var(--ha-font-family-code, monospace);
    letter-spacing: 1px;
    flex-shrink: 0;
  }
  .code.fixed {
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
  }
  .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 12px;
    line-height: 18px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  .badge ha-icon {
    --mdc-icon-size: 14px;
  }
  .badge.accent {
    background: rgba(var(--rgb-primary-color), 0.14);
    color: var(--primary-color);
  }
  .badge.warning {
    background: rgba(var(--rgb-warning-color, 255, 166, 0), 0.18);
    color: var(--warning-color);
  }
  ha-alert {
    display: block;
    margin: 8px 0;
  }
  ha-form {
    display: block;
  }

  /* Master-detail layout */
  .master-detail {
    display: grid;
    grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }
  .master-detail.narrow {
    grid-template-columns: minmax(0, 1fr);
  }
  .list {
    padding: 0 0 8px;
  }
  .list-item {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 10px 16px;
    box-sizing: border-box;
    border: none;
    background: none;
    text-align: start;
    color: var(--primary-text-color);
    font: inherit;
    cursor: pointer;
    border-inline-start: 3px solid transparent;
  }
  .list-item:hover {
    background: var(--secondary-background-color);
  }
  .list-item.selected {
    background: rgba(var(--rgb-primary-color), 0.08);
    border-inline-start-color: var(--primary-color);
  }
  .list-item .text {
    flex: 1;
    min-width: 0;
  }
  .list-item .primary {
    font-size: 15px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .list-item .secondary {
    margin-top: 2px;
    font-size: 13px;
    color: var(--secondary-text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .list-item .badges {
    margin-top: 4px;
  }
  .empty {
    padding: 8px 16px 16px;
    color: var(--secondary-text-color);
    line-height: 1.5;
  }
  .placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    min-height: 240px;
    padding: 24px;
    text-align: center;
    color: var(--secondary-text-color);
  }
  .placeholder ha-icon {
    --mdc-icon-size: 48px;
    opacity: 0.5;
  }
  .editor-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 16px 8px;
  }
  .editor-header .title {
    flex: 1;
    font-size: 20px;
    font-weight: 500;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border: none;
    border-radius: 50%;
    background: none;
    color: var(--secondary-text-color);
    cursor: pointer;
  }
  .icon-button:hover {
    background: var(--secondary-background-color);
  }

  /* Choice tiles */
  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 8px;
    margin: 8px 0 16px;
  }
  .tile {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    border: 1px solid var(--divider-color);
    border-radius: 12px;
    background: none;
    color: var(--primary-text-color);
    font: inherit;
    text-align: start;
    cursor: pointer;
  }
  .tile:hover {
    border-color: var(--primary-color);
  }
  .tile.selected {
    border-color: var(--primary-color);
    background: rgba(var(--rgb-primary-color), 0.08);
    box-shadow: inset 0 0 0 1px var(--primary-color);
  }
  .tile .tile-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
  }
  .tile .tile-title ha-icon {
    color: var(--primary-color);
  }
  .tile .tile-desc {
    font-size: 13px;
    line-height: 1.4;
    color: var(--secondary-text-color);
  }

  /* Switch rows */
  .switch-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 0;
    border-bottom: 1px solid var(--divider-color);
  }
  .switch-row:last-child {
    border-bottom: none;
  }
  .switch-row ha-icon {
    color: var(--secondary-text-color);
    flex-shrink: 0;
  }
  .switch-row .text {
    flex: 1;
    min-width: 0;
  }
  .switch-row .heading {
    font-size: 15px;
  }
  .switch-row .description {
    margin-top: 2px;
    font-size: 13px;
    line-height: 1.4;
    color: var(--secondary-text-color);
  }
  .nested {
    padding: 0 0 8px 40px;
  }
  .unsaved {
    font-size: 13px;
    color: var(--secondary-text-color);
  }
`;
