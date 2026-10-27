// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

interface IBalance { function balanceOf(address) external view returns (uint256); }

/// NPCSHOOD v2: 5,000 pixel NPCs in hoodies on BNB Chain.
/// Free mint, 2 per wallet; each NFT carries a small mint fee (default 0.0002 BNB) paid to the owner.
contract NPCSHOOD is ERC721, ERC2981, Ownable, ReentrancyGuard {
    using Strings for uint256;

    uint256 public constant MAX_SUPPLY = 5000;

    uint256 public price = 0.0002 ether;   // per NFT, owner can change
    uint256 public maxPerWallet = 2;       // owner can change
    address public agentId = 0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F; // Binance .ai Agent ID
    bool public requireAgentId = true;
    bool public mintOpen;
    string public baseURI;
    uint256 public totalMinted;
    address payable public payee;
    mapping(address => uint256) public mintedBy;

    event Minted(address indexed to, uint256 indexed firstId, uint256 quantity);

    error NoAgentId(); error MintClosed(); error BadQuantity(); error OverLimit(); error SoldOut();
    error Underpaid(); error PayFailed();

    constructor(string memory base) ERC721("NPCSHOOD", "NPCS") Ownable(msg.sender) {
        baseURI = base;
        payee = payable(msg.sender);
        _setDefaultRoyalty(msg.sender, 500); // 5%
    }

    function hasAgentId(address w) public view returns (bool) {
        if (!requireAgentId) return true;
        try IBalance(agentId).balanceOf(w) returns (uint256 b) { return b > 0; } catch { return false; }
    }

    function mintable(address w, uint256 q) public view returns (bool ok, uint256 left) {
        uint256 m = mintedBy[w];
        uint256 walletLeft = m >= maxPerWallet ? 0 : maxPerWallet - m;
        uint256 supplyLeft = MAX_SUPPLY - totalMinted;
        left = walletLeft < supplyLeft ? walletLeft : supplyLeft;
        ok = mintOpen && hasAgentId(w) && q > 0 && q <= left;
    }

    /// Same shape as v1 so agents keep working: (bnbWei, usdtUnits, npcUnits, paid)
    function quote(address, uint256 q) external view returns (uint256 bnbWei, uint256 usdtUnits, uint256 npcUnits, uint256 paid) {
        return (q * price, 0, 0, q);
    }

    function mint(uint256 q) external payable nonReentrant {
        if (!mintOpen) revert MintClosed();
        if (!hasAgentId(msg.sender)) revert NoAgentId();
        if (q == 0) revert BadQuantity();
        if (mintedBy[msg.sender] + q > maxPerWallet) revert OverLimit();
        if (totalMinted + q > MAX_SUPPLY) revert SoldOut();
        uint256 cost = q * price;
        if (msg.value < cost) revert Underpaid();
        uint256 first = totalMinted + 1;
        mintedBy[msg.sender] += q;
        totalMinted += q;
        for (uint256 i; i < q; ++i) _mint(msg.sender, first + i);
        emit Minted(msg.sender, first, q);
        if (cost > 0) { (bool s, ) = payee.call{value: cost}(""); if (!s) revert PayFailed(); }
        if (msg.value > cost) { (bool r, ) = payable(msg.sender).call{value: msg.value - cost}(""); if (!r) revert PayFailed(); }
    }

    // ---------------- owner
    /// Airdrop the next ids in order, one per address (used to carry v1 holders over with the same ids).
    function airdrop(address[] calldata to) external onlyOwner {
        uint256 n = to.length;
        if (totalMinted + n > MAX_SUPPLY) revert SoldOut();
        uint256 first = totalMinted + 1;
        totalMinted += n;
        for (uint256 i; i < n; ++i) _mint(to[i], first + i);
    }
    function setPrice(uint256 p) external onlyOwner { price = p; }
    function setMaxPerWallet(uint256 m) external onlyOwner { maxPerWallet = m; }
    function setMintOpen(bool v) external onlyOwner { mintOpen = v; }
    function setBaseURI(string calldata b) external onlyOwner { baseURI = b; }
    function setAgentGate(address a, bool required) external onlyOwner { agentId = a; requireAgentId = required; }
    function setPayee(address payable p) external onlyOwner { payee = p; }
    function setRoyalty(address r, uint96 bps) external onlyOwner { _setDefaultRoyalty(r, bps); }

    function tokenURI(uint256 id) public view override returns (string memory) {
        _requireOwned(id);
        return string.concat(baseURI, id.toString(), ".json");
    }
    function totalSupply() external view returns (uint256) { return totalMinted; }
    function supportsInterface(bytes4 i) public view override(ERC721, ERC2981) returns (bool) { return super.supportsInterface(i); }
}
