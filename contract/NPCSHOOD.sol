// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

interface IAggregator { function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80); }
interface IBalance { function balanceOf(address) external view returns (uint256); }

/// NPCSHOOD: 5,000 pixel NPCs in hoodies on BNB Chain.
/// 2 free per wallet, then $1 each (BNB via Chainlink, 1 USDT, or the project token), 12 per wallet max.
contract NPCSHOOD is ERC721, ERC2981, Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;
    using Strings for uint256;

    uint256 public constant MAX_SUPPLY = 5000;
    uint256 public constant FREE_PER_WALLET = 2;
    uint256 public constant MAX_PER_WALLET = 12;

    IAggregator public constant BNB_USD = IAggregator(0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE);
    address public constant USDT = 0x55d398326f99059fF775485246999027B3197955; // 18 decimals

    address public agentId = 0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F; // Binance .ai Agent ID
    bool public requireAgentId = true;
    address public npcToken;            // optional project token, set later
    uint256 public npcPerPiece = 10_000 ether;
    uint256 public fallbackBnbPrice = 0.002 ether; // used only if the feed is stale
    bool public mintOpen;
    string public baseURI;
    uint256 public totalMinted;
    address payable public payee;
    mapping(address => uint256) public mintedBy;

    event Minted(address indexed to, uint256 indexed firstId, uint256 quantity);

    error NoAgentId(); error MintClosed(); error BadQuantity(); error OverLimit(); error SoldOut();
    error Underpaid(); error PayFailed(); error BadToken();

    constructor(string memory base) ERC721("NPCSHOOD", "NPCS") Ownable(msg.sender) {
        baseURI = base;
        payee = payable(msg.sender);
        _setDefaultRoyalty(msg.sender, 500); // 5%
    }

    // ---------------- reads used by the site and agent prompt
    function hasAgentId(address w) public view returns (bool) {
        if (!requireAgentId) return true;
        try IBalance(agentId).balanceOf(w) returns (uint256 b) { return b > 0; } catch { return false; }
    }

    function mintable(address w, uint256 q) public view returns (bool ok, uint256 left) {
        uint256 walletLeft = MAX_PER_WALLET - mintedBy[w];
        uint256 supplyLeft = MAX_SUPPLY - totalMinted;
        left = walletLeft < supplyLeft ? walletLeft : supplyLeft;
        ok = mintOpen && hasAgentId(w) && q > 0 && q <= left;
    }

    function paidCount(address w, uint256 q) public view returns (uint256) {
        uint256 m = mintedBy[w];
        uint256 freeLeft = m >= FREE_PER_WALLET ? 0 : FREE_PER_WALLET - m;
        return q > freeLeft ? q - freeLeft : 0;
    }

    function bnbPerDollar() public view returns (uint256) {
        try BNB_USD.latestRoundData() returns (uint80, int256 answer, uint256, uint256 updatedAt, uint80) {
            if (answer > 0 && block.timestamp - updatedAt < 2 hours) {
                return (1e18 * 1e8) / uint256(answer); // feed has 8 decimals
            }
        } catch {}
        return fallbackBnbPrice;
    }

    function quote(address w, uint256 q) external view returns (uint256 bnbWei, uint256 usdtUnits, uint256 npcUnits, uint256 paid) {
        paid = paidCount(w, q);
        bnbWei = paid * bnbPerDollar();
        usdtUnits = paid * 1e18;
        npcUnits = paid * npcPerPiece;
    }

    // ---------------- minting
    function _check(uint256 q) internal view {
        if (!mintOpen) revert MintClosed();
        if (!hasAgentId(msg.sender)) revert NoAgentId();
        if (q == 0 || q > MAX_PER_WALLET) revert BadQuantity();
        if (mintedBy[msg.sender] + q > MAX_PER_WALLET) revert OverLimit();
        if (totalMinted + q > MAX_SUPPLY) revert SoldOut();
    }

    function _mintMany(uint256 q) internal {
        uint256 first = totalMinted + 1;
        mintedBy[msg.sender] += q;
        totalMinted += q;
        for (uint256 i; i < q; ++i) _mint(msg.sender, first + i);
        emit Minted(msg.sender, first, q);
    }

    function mint(uint256 q) external payable nonReentrant {
        _check(q);
        uint256 cost = paidCount(msg.sender, q) * bnbPerDollar();
        if (msg.value < cost) revert Underpaid();
        _mintMany(q);
        if (cost > 0) { (bool s, ) = payee.call{value: cost}(""); if (!s) revert PayFailed(); }
        if (msg.value > cost) { (bool r, ) = payable(msg.sender).call{value: msg.value - cost}(""); if (!r) revert PayFailed(); }
    }

    function mintWithToken(uint256 q, address token) external nonReentrant {
        _check(q);
        uint256 paid = paidCount(msg.sender, q);
        uint256 cost;
        if (token == USDT) cost = paid * 1e18;
        else if (token != address(0) && token == npcToken) cost = paid * npcPerPiece;
        else revert BadToken();
        _mintMany(q);
        if (cost > 0) IERC20(token).safeTransferFrom(msg.sender, payee, cost);
    }

    // ---------------- owner
    function setMintOpen(bool v) external onlyOwner { mintOpen = v; }
    function setBaseURI(string calldata b) external onlyOwner { baseURI = b; }
    function setAgentGate(address a, bool required) external onlyOwner { agentId = a; requireAgentId = required; }
    function setNpcToken(address t, uint256 perPiece) external onlyOwner { npcToken = t; npcPerPiece = perPiece; }
    function setFallbackBnbPrice(uint256 p) external onlyOwner { fallbackBnbPrice = p; }
    function setPayee(address payable p) external onlyOwner { payee = p; }
    function setRoyalty(address r, uint96 bps) external onlyOwner { _setDefaultRoyalty(r, bps); }
    function ownerMint(address to, uint256 q) external onlyOwner {
        if (totalMinted + q > MAX_SUPPLY) revert SoldOut();
        uint256 first = totalMinted + 1; totalMinted += q;
        for (uint256 i; i < q; ++i) _mint(to, first + i);
        emit Minted(to, first, q);
    }

    // ---------------- metadata
    function tokenURI(uint256 id) public view override returns (string memory) {
        _requireOwned(id);
        return string.concat(baseURI, id.toString(), ".json");
    }
    function totalSupply() external view returns (uint256) { return totalMinted; }
    function supportsInterface(bytes4 i) public view override(ERC721, ERC2981) returns (bool) { return super.supportsInterface(i); }
}
