/**
 * Global Remote Control Service
 * Coordinates API calls for fleet metrics, batch dispatch, and global history.
 */

import {
  getFleetOverview,
  issueBatchCommand,
  getGlobalCommands,
  exportGlobalCommandsToCsv,
  getCommandDetails,
} from "../../../services/commandService";
import { getComputers } from "../../../services/computerService";

export {
  getFleetOverview,
  issueBatchCommand,
  getGlobalCommands,
  exportGlobalCommandsToCsv,
  getCommandDetails,
  getComputers,
};
