const hre = require("hardhat");

async function main() {
  console.log("🚀 Déploiement du contrat EnergyExchange...");
  
  const EnergyExchange = await hre.ethers.getContractFactory("EnergyExchange");
  const energyExchange = await EnergyExchange.deploy();
  
  await energyExchange.waitForDeployment();
  
  const address = await energyExchange.getAddress();
  console.log(`✅ Contract déployé à l'adresse: ${address}`);
  
  // Enregistrer l'adresse dans un fichier
  const fs = require('fs');
  fs.writeFileSync('contract-address.json', JSON.stringify({ address }, null, 2));
  
  console.log("📝 Adresse sauvegardée dans contract-address.json");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});