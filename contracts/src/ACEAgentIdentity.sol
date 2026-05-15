// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/**
 * @title ACEAgentIdentity — ACE underwriting certificate, ERC-8004-flavored.
 * @notice An ERC-721 Identity Registry that binds an NFT to an immutable
 *         `identityHash` representing the full applicant declaration
 *         (model, system prompt, tools, wallet, spending policy, endpoint
 *         config, behavioral config). Any mutation to the declaration
 *         changes the off-chain hash, so `verifyIdentity` will return
 *         false and downstream consumers can treat coverage as void.
 *
 * @dev Designed to be ERC-8004 Identity-Registry-compatible without
 *      pulling in external dependencies. This is a demo-grade
 *      implementation for a university risk-management competition; a
 *      production deployment should swap in OpenZeppelin's
 *      `ERC721URIStorage` + `AccessControl`.
 *
 *      Paper anchor:
 *      Li et al. "Five Attacks on x402 Agentic Payment Protocol",
 *      arXiv:2605.11781 §6.3 — explicitly recommends ERC-8004 as the
 *      complementary agent-registry layer carrying trust metadata
 *      around x402 services.
 */
contract ACEAgentIdentity {
    // --- Roles ------------------------------------------------------------
    address public owner;
    address public underwriter;

    // --- ERC-721 minimal storage -----------------------------------------
    string public name = "ACE Agent Identity";
    string public symbol = "ACE-AGENT";
    uint256 private _nextTokenId = 1;

    mapping(uint256 => address) private _ownerOf;
    mapping(address => uint256) private _balanceOf;
    mapping(uint256 => address) private _approved;
    mapping(address => mapping(address => bool)) private _operatorApprovals;

    // --- ACE-specific per-token state ------------------------------------
    mapping(uint256 => string) private _tokenURI;
    mapping(uint256 => bytes32) private _identityHash;
    mapping(uint256 => uint256) private _underwrittenAt; // unix seconds
    mapping(uint256 => string) private _agentName; // human-readable handle

    // --- Events ----------------------------------------------------------
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);

    /// @notice Emitted on a successful underwriting mint.
    event Underwritten(
        uint256 indexed tokenId,
        address indexed agentOwner,
        string agentName,
        bytes32 identityHash,
        string agentURI
    );

    /// @notice Emitted when a verifier checks an on-chain hash against a candidate.
    event IdentityVerified(uint256 indexed tokenId, bytes32 candidate, bool matched);

    event UnderwriterChanged(address indexed previous, address indexed current);
    event OwnershipTransferred(address indexed previous, address indexed current);

    // --- Errors ----------------------------------------------------------
    error NotOwner();
    error NotUnderwriter();
    error TokenDoesNotExist();
    error NotAuthorized();
    error TransferToZero();
    error AlreadyMinted();

    // --- Constructor -----------------------------------------------------
    constructor(address initialUnderwriter) {
        owner = msg.sender;
        underwriter = initialUnderwriter;
        emit OwnershipTransferred(address(0), msg.sender);
        emit UnderwriterChanged(address(0), initialUnderwriter);
    }

    // --- Admin -----------------------------------------------------------
    function setUnderwriter(address newUnderwriter) external {
        if (msg.sender != owner) revert NotOwner();
        emit UnderwriterChanged(underwriter, newUnderwriter);
        underwriter = newUnderwriter;
    }

    function transferOwnership(address newOwner) external {
        if (msg.sender != owner) revert NotOwner();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    // --- Underwriting mint ----------------------------------------------
    /**
     * @notice Mint a new ACE certificate NFT to `to`, binding it to
     *         `identityHash` (off-chain canonical hash of the full
     *         Applicant declaration).
     * @dev    Only the ACE underwriter may mint. The agentURI MUST
     *         resolve to a JSON document carrying the registration
     *         metadata (paper §6.3 / ERC-8004 registration schema).
     */
    function mintCertificate(
        address to,
        string calldata agentName_,
        bytes32 identityHash,
        string calldata agentURI
    ) external returns (uint256 tokenId) {
        if (msg.sender != underwriter) revert NotUnderwriter();
        if (to == address(0)) revert TransferToZero();
        tokenId = _nextTokenId++;
        _ownerOf[tokenId] = to;
        _balanceOf[to] += 1;
        _tokenURI[tokenId] = agentURI;
        _identityHash[tokenId] = identityHash;
        _underwrittenAt[tokenId] = block.timestamp;
        _agentName[tokenId] = agentName_;
        emit Transfer(address(0), to, tokenId);
        emit Underwritten(tokenId, to, agentName_, identityHash, agentURI);
    }

    // --- Identity verification ------------------------------------------
    /**
     * @notice Return true iff the current applicant declaration's
     *         off-chain canonical hash matches the one bound at mint.
     *         A mismatch means the agent has been modified post-issue
     *         and downstream consumers should treat coverage as void.
     */
    function verifyIdentity(uint256 tokenId, bytes32 candidate) external returns (bool matched) {
        if (_ownerOf[tokenId] == address(0)) revert TokenDoesNotExist();
        matched = (_identityHash[tokenId] == candidate);
        emit IdentityVerified(tokenId, candidate, matched);
    }

    function identityHashOf(uint256 tokenId) external view returns (bytes32) {
        if (_ownerOf[tokenId] == address(0)) revert TokenDoesNotExist();
        return _identityHash[tokenId];
    }

    function underwrittenAt(uint256 tokenId) external view returns (uint256) {
        return _underwrittenAt[tokenId];
    }

    function agentName(uint256 tokenId) external view returns (string memory) {
        return _agentName[tokenId];
    }

    // --- ERC-721 read API -----------------------------------------------
    function ownerOf(uint256 tokenId) public view returns (address) {
        address o = _ownerOf[tokenId];
        if (o == address(0)) revert TokenDoesNotExist();
        return o;
    }

    function balanceOf(address account) external view returns (uint256) {
        return _balanceOf[account];
    }

    function tokenURI(uint256 tokenId) external view returns (string memory) {
        if (_ownerOf[tokenId] == address(0)) revert TokenDoesNotExist();
        return _tokenURI[tokenId];
    }

    function getApproved(uint256 tokenId) external view returns (address) {
        if (_ownerOf[tokenId] == address(0)) revert TokenDoesNotExist();
        return _approved[tokenId];
    }

    function isApprovedForAll(address account, address operator) external view returns (bool) {
        return _operatorApprovals[account][operator];
    }

    // --- ERC-721 write API ----------------------------------------------
    function approve(address to, uint256 tokenId) external {
        address o = ownerOf(tokenId);
        if (msg.sender != o && !_operatorApprovals[o][msg.sender]) revert NotAuthorized();
        _approved[tokenId] = to;
        emit Approval(o, to, tokenId);
    }

    function setApprovalForAll(address operator, bool approved) external {
        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    function transferFrom(address from, address to, uint256 tokenId) public {
        if (to == address(0)) revert TransferToZero();
        address o = ownerOf(tokenId);
        if (o != from) revert NotAuthorized();
        if (
            msg.sender != o && _approved[tokenId] != msg.sender
                && !_operatorApprovals[o][msg.sender]
        ) revert NotAuthorized();
        _approved[tokenId] = address(0);
        _balanceOf[from] -= 1;
        _balanceOf[to] += 1;
        _ownerOf[tokenId] = to;
        emit Transfer(from, to, tokenId);
    }

    function safeTransferFrom(address from, address to, uint256 tokenId) external {
        transferFrom(from, to, tokenId);
    }

    function safeTransferFrom(address from, address to, uint256 tokenId, bytes calldata)
        external
    {
        transferFrom(from, to, tokenId);
    }

    // --- ERC-165 ---------------------------------------------------------
    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return interfaceId == 0x80ac58cd // ERC-721
            || interfaceId == 0x5b5e139f // ERC-721 Metadata
            || interfaceId == 0x01ffc9a7; // ERC-165
    }
}
