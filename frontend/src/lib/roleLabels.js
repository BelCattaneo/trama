export function operationLabels(role) {
  if (role === "producer") {
    return {
      nav: "Mi oferta",
      action: "Subir oferta",
      firstAction: "Subir tu primera oferta",
    };
  }
  if (role === "consumer") {
    return {
      nav: "Mis pedidos",
      action: "Subir pedido",
      firstAction: "Subir tu primer pedido",
    };
  }
  return {
    nav: "Mis operaciones",
    action: "Subir operación",
    firstAction: "Subir tu primera operación",
  };
}
