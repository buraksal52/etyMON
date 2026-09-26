// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {RewardPool} from "../src/RewardPool.sol";

interface Vm {
    function startBroadcast() external;
    function stopBroadcast() external;
}

contract DeployRewardPool {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function run() external returns (RewardPool pool) {
        vm.startBroadcast();
        pool = new RewardPool();
        vm.stopBroadcast();
    }
}
