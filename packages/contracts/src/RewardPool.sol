// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

contract RewardPool {
    error NotOwner();
    error NotAuthorized();
    error ZeroAddress();
    error ZeroAmount();
    error ReasonAlreadyPaid();
    error InsufficientBalance();
    error TransferFailed();

    address public immutable owner;
    mapping(address => bool) public authorized;
    mapping(bytes32 => bool) private paidReasons;

    event AuthorizedAccountUpdated(address indexed account, bool allowed);
    event Deposited(address indexed from, uint256 amount);
    event RewardPaid(
        bytes32 indexed eventId,
        bytes32 indexed participantId,
        bytes32 indexed reasonId,
        address recipient,
        uint256 amount
    );
    event Withdrawn(address indexed recipient, uint256 amount);

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyAuthorized() {
        if (msg.sender != owner && !authorized[msg.sender]) revert NotAuthorized();
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    receive() external payable {
        emit Deposited(msg.sender, msg.value);
    }

    function deposit() external payable {
        if (msg.value == 0) revert ZeroAmount();
        emit Deposited(msg.sender, msg.value);
    }

    function setAuthorized(address account, bool allowed) external onlyOwner {
        if (account == address(0)) revert ZeroAddress();
        authorized[account] = allowed;
        emit AuthorizedAccountUpdated(account, allowed);
    }

    function rewardParticipant(
        bytes32 eventId,
        bytes32 participantId,
        bytes32 reasonId,
        address payable recipient,
        uint256 amount
    ) external onlyAuthorized {
        if (recipient == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        if (paidReasons[reasonId]) revert ReasonAlreadyPaid();
        if (address(this).balance < amount) revert InsufficientBalance();

        paidReasons[reasonId] = true;
        (bool success,) = recipient.call{value: amount}("");
        if (!success) revert TransferFailed();

        emit RewardPaid(eventId, participantId, reasonId, recipient, amount);
    }

    function isPaid(bytes32 reasonId) external view returns (bool) {
        return paidReasons[reasonId];
    }

    function withdraw(address payable recipient, uint256 amount) external onlyOwner {
        if (recipient == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        if (address(this).balance < amount) revert InsufficientBalance();
        (bool success,) = recipient.call{value: amount}("");
        if (!success) revert TransferFailed();
        emit Withdrawn(recipient, amount);
    }
}
