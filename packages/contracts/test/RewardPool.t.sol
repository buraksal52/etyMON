// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {RewardPool} from "../src/RewardPool.sol";

interface Vm {
    function deal(address account, uint256 newBalance) external;
    function prank(address sender) external;
    function expectEmit(bool checkTopic1, bool checkTopic2, bool checkTopic3, bool checkData) external;
    function expectRevert(bytes4 revertData) external;
}

contract RewardPoolTest {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    RewardPool private pool;
    address private backend = address(0xBEEF);
    address payable private recipient = payable(address(0xCAFE));
    bytes32 private eventId = keccak256("event");
    bytes32 private participantId = keccak256("participant");
    bytes32 private reasonId = keccak256("reason");

    event RewardPaid(
        bytes32 indexed eventId,
        bytes32 indexed participantId,
        bytes32 indexed reasonId,
        address recipient,
        uint256 amount
    );

    function setUp() public {
        pool = new RewardPool();
        pool.setAuthorized(backend, true);
        vm.deal(address(this), 2 ether);
    }

    function testDeposit() public {
        pool.deposit{value: 1 ether}();
        require(address(pool).balance == 1 ether, "incorrect pool balance");
    }

    function testAuthorizedRewardAndEvent() public {
        pool.deposit{value: 1 ether}();

        vm.expectEmit(true, true, true, true);
        emit RewardPaid(eventId, participantId, reasonId, recipient, 0.25 ether);
        vm.prank(backend);
        pool.rewardParticipant(eventId, participantId, reasonId, recipient, 0.25 ether);

        require(recipient.balance == 0.25 ether, "recipient not paid");
        require(address(pool).balance == 0.75 ether, "incorrect remaining balance");
        require(_isPaid(reasonId), "reason not marked paid");
    }

    function testUnauthorizedRewardReverts() public {
        pool.deposit{value: 1 ether}();

        vm.prank(address(0x1234));
        vm.expectRevert(RewardPool.NotAuthorized.selector);
        pool.rewardParticipant(eventId, participantId, reasonId, recipient, 0.25 ether);
    }

    function testDuplicateReasonReverts() public {
        pool.deposit{value: 1 ether}();
        vm.prank(backend);
        pool.rewardParticipant(eventId, participantId, reasonId, recipient, 0.25 ether);

        vm.prank(backend);
        vm.expectRevert(RewardPool.ReasonAlreadyPaid.selector);
        pool.rewardParticipant(eventId, participantId, reasonId, recipient, 0.25 ether);
    }

    function _isPaid(bytes32 id) private view returns (bool) {
        return pool.isPaid(id);
    }
}
