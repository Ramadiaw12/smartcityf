// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title EnergyExchange
 * @dev Smart Contract pour l'échange d'énergie entre maisons
 * @author SmartCas EnergyChain
 */
contract EnergyExchange {
    
    // ============================================
    // STRUCTURES
    // ============================================
    
    struct House {
        uint256 id;
        string name;
        address owner;
        int256 energyBalance;  // Positif = surplus, Négatif = déficit
        uint256 totalConsumed;
        uint256 totalProduced;
        uint256 totalTransferredIn;
        uint256 totalTransferredOut;
        bool isRegistered;
    }
    
    struct EnergyTransfer {
        uint256 transferId;
        uint256 fromHouseId;
        uint256 toHouseId;
        address fromAddress;
        address toAddress;
        uint256 amountKWh;
        uint256 timestamp;
        bool isCompleted;
        string transactionHash;
    }
    
    // ============================================
    // VARIABLES D'ÉTAT
    // ============================================
    
    mapping(uint256 => House) public houses;
    mapping(uint256 => EnergyTransfer[]) public houseTransfers;
    EnergyTransfer[] public allTransfers;
    
    uint256 public totalEnergyTransferred;
    uint256 public totalTransactions;
    address public contractOwner;
    
    // Événements
    event HouseRegistered(uint256 indexed houseId, string name, address owner);
    event EnergyTransferred(
        uint256 indexed transferId,
        uint256 indexed fromHouse,
        uint256 indexed toHouse,
        uint256 amountKWh,
        uint256 timestamp
    );
    event EnergyBalanceUpdated(uint256 indexed houseId, int256 newBalance);
    
    // ============================================
    // MODIFIERS
    // ============================================
    
    modifier onlyOwner() {
        require(msg.sender == contractOwner, "Seul le propriétaire peut appeler cette fonction");
        _;
    }
    
    modifier houseExists(uint256 _houseId) {
        require(houses[_houseId].isRegistered, "Cette maison n'existe pas");
        _;
    }
    
    // ============================================
    // CONSTRUCTEUR
    // ============================================
    
    constructor() {
        contractOwner = msg.sender;
    }
    
    // ============================================
    // FONCTIONS PRINCIPALES
    // ============================================
    
    /**
     * @dev Enregistrer une nouvelle maison
     * @param _houseId ID unique de la maison
     * @param _name Nom de la maison
     * @param _owner Adresse du propriétaire
     */
    function registerHouse(
        uint256 _houseId,
        string memory _name,
        address _owner
    ) public onlyOwner {
        require(!houses[_houseId].isRegistered, "Maison déjà enregistrée");
        
        houses[_houseId] = House({
            id: _houseId,
            name: _name,
            owner: _owner,
            energyBalance: 0,
            totalConsumed: 0,
            totalProduced: 0,
            totalTransferredIn: 0,
            totalTransferredOut: 0,
            isRegistered: true
        });
        
        emit HouseRegistered(_houseId, _name, _owner);
    }
    
    /**
     * @dev Mettre à jour le bilan énergétique d'une maison
     * @param _houseId ID de la maison
     * @param _newBalance Nouveau bilan (positif = surplus, négatif = déficit)
     */
    function updateEnergyBalance(
        uint256 _houseId,
        int256 _newBalance
    ) public onlyOwner houseExists(_houseId) {
        houses[_houseId].energyBalance = _newBalance;
        emit EnergyBalanceUpdated(_houseId, _newBalance);
    }
    
    /**
     * @dev Transférer de l'énergie entre deux maisons
     * @param _fromHouseId Maison qui donne l'énergie (surplus)
     * @param _toHouseId Maison qui reçoit l'énergie (déficit)
     * @param _amountKWh Quantité d'énergie en kWh
     */
    function transferEnergy(
        uint256 _fromHouseId,
        uint256 _toHouseId,
        uint256 _amountKWh
    ) public houseExists(_fromHouseId) houseExists(_toHouseId) {
        require(_fromHouseId != _toHouseId, "Impossible de transférer à soi-même");
        require(_amountKWh > 0, "La quantité doit être positive");
        require(houses[_fromHouseId].energyBalance >= int256(_amountKWh), "Surplus insuffisant");
        
        // Mise à jour des bilans
        houses[_fromHouseId].energyBalance -= int256(_amountKWh);
        houses[_toHouseId].energyBalance += int256(_amountKWh);
        
        // Mise à jour des statistiques
        houses[_fromHouseId].totalTransferredOut += _amountKWh;
        houses[_toHouseId].totalTransferredIn += _amountKWh;
        
        // Créer la transaction
        uint256 transferId = allTransfers.length;
        
        EnergyTransfer memory newTransfer = EnergyTransfer({
            transferId: transferId,
            fromHouseId: _fromHouseId,
            toHouseId: _toHouseId,
            fromAddress: houses[_fromHouseId].owner,
            toAddress: houses[_toHouseId].owner,
            amountKWh: _amountKWh,
            timestamp: block.timestamp,
            isCompleted: true,
            transactionHash: ""
        });
        
        allTransfers.push(newTransfer);
        houseTransfers[_fromHouseId].push(newTransfer);
        houseTransfers[_toHouseId].push(newTransfer);
        
        // Mise à jour des statistiques globales
        totalEnergyTransferred += _amountKWh;
        totalTransactions++;
        
        emit EnergyTransferred(transferId, _fromHouseId, _toHouseId, _amountKWh, block.timestamp);
    }
    
    /**
     * @dev Transférer de l'énergie avec hash de transaction
     * @param _fromHouseId Maison donneuse
     * @param _toHouseId Maison receveuse
     * @param _amountKWh Quantité d'énergie
     * @param _transactionHash Hash de la transaction blockchain
     */
    function transferEnergyWithHash(
        uint256 _fromHouseId,
        uint256 _toHouseId,
        uint256 _amountKWh,
        string memory _transactionHash
    ) public houseExists(_fromHouseId) houseExists(_toHouseId) {
        require(_fromHouseId != _toHouseId, "Impossible de transférer à soi-même");
        require(_amountKWh > 0, "La quantité doit être positive");
        require(houses[_fromHouseId].energyBalance >= int256(_amountKWh), "Surplus insuffisant");
        
        houses[_fromHouseId].energyBalance -= int256(_amountKWh);
        houses[_toHouseId].energyBalance += int256(_amountKWh);
        
        houses[_fromHouseId].totalTransferredOut += _amountKWh;
        houses[_toHouseId].totalTransferredIn += _amountKWh;
        
        uint256 transferId = allTransfers.length;
        
        EnergyTransfer memory newTransfer = EnergyTransfer({
            transferId: transferId,
            fromHouseId: _fromHouseId,
            toHouseId: _toHouseId,
            fromAddress: houses[_fromHouseId].owner,
            toAddress: houses[_toHouseId].owner,
            amountKWh: _amountKWh,
            timestamp: block.timestamp,
            isCompleted: true,
            transactionHash: _transactionHash
        });
        
        allTransfers.push(newTransfer);
        houseTransfers[_fromHouseId].push(newTransfer);
        houseTransfers[_toHouseId].push(newTransfer);
        
        totalEnergyTransferred += _amountKWh;
        totalTransactions++;
        
        emit EnergyTransferred(transferId, _fromHouseId, _toHouseId, _amountKWh, block.timestamp);
    }
    
    // ============================================
    // FONCTIONS DE LECTURE
    // ============================================
    
    /**
     * @dev Obtenir les informations d'une maison
     */
    function getHouseInfo(uint256 _houseId) public view returns (
        uint256 id,
        string memory name,
        address owner,
        int256 energyBalance,
        uint256 totalConsumed,
        uint256 totalProduced,
        uint256 totalTransferredIn,
        uint256 totalTransferredOut
    ) {
        House memory house = houses[_houseId];
        require(house.isRegistered, "Maison non trouvée");
        return (
            house.id,
            house.name,
            house.owner,
            house.energyBalance,
            house.totalConsumed,
            house.totalProduced,
            house.totalTransferredIn,
            house.totalTransferredOut
        );
    }
    
    /**
     * @dev Obtenir l'historique des transferts d'une maison
     */
    function getHouseTransfers(uint256 _houseId) public view returns (EnergyTransfer[] memory) {
        return houseTransfers[_houseId];
    }
    
    /**
     * @dev Obtenir tous les transferts
     */
    function getAllTransfers() public view returns (EnergyTransfer[] memory) {
        return allTransfers;
    }
    
    /**
     * @dev Obtenir les statistiques globales
     */
    function getGlobalStats() public view returns (
        uint256 totalEnergy,
        uint256 totalTx,
        uint256 totalHouses
    ) {
        uint256 houseCount = 0;
        // Compter les maisons enregistrées (limité à 10 pour le gas)
        for (uint256 i = 1; i <= 10; i++) {
            if (houses[i].isRegistered) houseCount++;
        }
        return (totalEnergyTransferred, totalTransactions, houseCount);
    }
    
    /**
     * @dev Calculer le CO₂ économisé (1 kWh = 0.45 kg CO₂ en moyenne au Maroc)
     */
    function getCO2Saved() public view returns (uint256) {
        return (totalEnergyTransferred * 450) / 1000; // en kg
    }
}