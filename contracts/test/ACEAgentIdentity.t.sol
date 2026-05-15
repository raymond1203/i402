// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "forge-std/Test.sol";
import "../src/ACEAgentIdentity.sol";

contract ACEAgentIdentityTest is Test {
    ACEAgentIdentity internal ace;
    address internal deployer = address(0xA1);
    address internal underwriter = address(0xA2);
    address internal applicant = address(0xB1);
    address internal stranger = address(0xC1);

    bytes32 internal constant SAMPLE_HASH =
        0x1111111111111111111111111111111111111111111111111111111111111111;
    bytes32 internal constant DIFFERENT_HASH =
        0x2222222222222222222222222222222222222222222222222222222222222222;

    function setUp() public {
        vm.startPrank(deployer);
        ace = new ACEAgentIdentity(underwriter);
        vm.stopPrank();
    }

    function test_DeploymentSetsOwnerAndUnderwriter() public view {
        assertEq(ace.owner(), deployer);
        assertEq(ace.underwriter(), underwriter);
    }

    function test_MintByUnderwriterSucceeds() public {
        vm.prank(underwriter);
        uint256 tokenId =
            ace.mintCertificate(applicant, "safe_paybot", SAMPLE_HASH, "ipfs://Q.../safe.json");
        assertEq(tokenId, 1);
        assertEq(ace.ownerOf(1), applicant);
        assertEq(ace.balanceOf(applicant), 1);
        assertEq(ace.tokenURI(1), "ipfs://Q.../safe.json");
        assertEq(ace.identityHashOf(1), SAMPLE_HASH);
        assertEq(ace.agentName(1), "safe_paybot");
        assertGt(ace.underwrittenAt(1), 0);
    }

    function test_MintByStrangerReverts() public {
        vm.prank(stranger);
        vm.expectRevert(ACEAgentIdentity.NotUnderwriter.selector);
        ace.mintCertificate(applicant, "x", SAMPLE_HASH, "ipfs://x");
    }

    function test_VerifyIdentityMatchingHash() public {
        vm.prank(underwriter);
        uint256 tokenId =
            ace.mintCertificate(applicant, "safe_paybot", SAMPLE_HASH, "ipfs://Q.../safe.json");
        bool matched = ace.verifyIdentity(tokenId, SAMPLE_HASH);
        assertTrue(matched);
    }

    function test_VerifyIdentityRejectsModifiedHash() public {
        // Mint with SAMPLE_HASH, then try to verify with DIFFERENT_HASH (simulating
        // the applicant having edited their system prompt one character).
        vm.prank(underwriter);
        uint256 tokenId =
            ace.mintCertificate(applicant, "safe_paybot", SAMPLE_HASH, "ipfs://Q.../safe.json");
        bool matched = ace.verifyIdentity(tokenId, DIFFERENT_HASH);
        assertFalse(matched);
    }

    function test_VerifyIdentityNonexistentTokenReverts() public {
        vm.expectRevert(ACEAgentIdentity.TokenDoesNotExist.selector);
        ace.verifyIdentity(999, SAMPLE_HASH);
    }

    function test_TokenIdsAreSequential() public {
        vm.startPrank(underwriter);
        uint256 a = ace.mintCertificate(applicant, "a", SAMPLE_HASH, "ipfs://a");
        uint256 b = ace.mintCertificate(applicant, "b", DIFFERENT_HASH, "ipfs://b");
        vm.stopPrank();
        assertEq(a, 1);
        assertEq(b, 2);
    }

    function test_SetUnderwriterByOwner() public {
        address newUw = address(0xDDD);
        vm.prank(deployer);
        ace.setUnderwriter(newUw);
        assertEq(ace.underwriter(), newUw);
    }

    function test_SetUnderwriterByStrangerReverts() public {
        vm.prank(stranger);
        vm.expectRevert(ACEAgentIdentity.NotOwner.selector);
        ace.setUnderwriter(stranger);
    }

    function test_TransferFromMovesOwnership() public {
        vm.prank(underwriter);
        uint256 tokenId =
            ace.mintCertificate(applicant, "safe_paybot", SAMPLE_HASH, "ipfs://Q.../safe.json");
        vm.prank(applicant);
        ace.transferFrom(applicant, stranger, tokenId);
        assertEq(ace.ownerOf(tokenId), stranger);
        // Identity hash and metadata are preserved across transfer — the
        // bond is to the agent, not the holder.
        assertEq(ace.identityHashOf(tokenId), SAMPLE_HASH);
    }

    function test_SupportsERC721Interface() public view {
        assertTrue(ace.supportsInterface(0x80ac58cd));
        assertTrue(ace.supportsInterface(0x5b5e139f));
        assertTrue(ace.supportsInterface(0x01ffc9a7));
        assertFalse(ace.supportsInterface(0xdeadbeef));
    }
}
