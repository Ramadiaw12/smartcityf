const path = require("path");

module.exports = {
  // Désactiver les fonctionnalités problématiques
  contracts_build_directory: path.join(__dirname, "build/contracts"),
  
  networks: {
    development: {
      host: "127.0.0.1",
      port: 7545,
      network_id: "1337",  // Ganache chainId par défaut
      gas: 6721975,
      gasPrice: 20000000000
    },
    ganache_cli: {
      host: "127.0.0.1",
      port: 8545,
      network_id: "5777",  // Ganache CLI chainId
      gas: 6721975
    }
  },
  
  compilers: {
    solc: {
      version: "0.8.19",
      optimizer: {
        enabled: true,
        runs: 200
      },
      evmVersion: "london"
    }
  },
  
  // Résoudre l'erreur uws
  mocha: {
    useColors: true,
    slow: 3000,
    timeout: 10000
  },
  
  db: {
    enabled: false
  }
};