using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

/// <summary>
/// AGIseedAgentBridge : Composant C# Unity pour relier un personnage/avatar 3D
/// au cerveau cognitif Liquid Mamba ODE d'AGIseed via socket TCP local.
/// 
/// Instructions d'intégration dans Unity :
/// 1. Attachez ce script à votre GameObject (ex: "Player", "Agent", ou "Robot").
/// 2. Assurez-vous qu'un Rigidbody et un Collider sont présents.
/// 3. Réglez le port TCP (par défaut 5555).
/// 4. Lancez le jeu sous Unity, puis lancez le monde Python UnityBridgeWorld.
/// </summary>
public class AGIseedAgentBridge : MonoBehaviour
{
    [Header("Configuration Réseau TCP")]
    public string host = "127.0.0.1";
    public int port = 5555;
    public bool isServer = true;

    [Header("Paramètres Physiques")]
    public float moveSpeedMultiplier = 10f;
    public float jumpForce = 5f;
    public int lidarRayCount = 16;
    public float lidarMaxDistance = 30f;

    private TcpListener serverListener;
    private TcpClient client;
    private NetworkStream stream;
    private Thread networkThread;
    private Rigidbody rb;

    private float[] currentActions = new float[25];
    private float[] observations = new float[45];
    private bool isRunning = false;

    void Start()
    {
        rb = GetComponent<Rigidbody>();
        if (rb == null)
        {
            Debug.LogWarning("[AGIseed] Aucun Rigidbody trouvé, ajout automatique d'un Rigidbody.");
            rb = gameObject.AddComponent<Rigidbody>();
        }

        if (isServer)
        {
            networkThread = new Thread(StartTcpServer);
            networkThread.IsBackground = true;
            networkThread.Start();
        }
    }

    void StartTcpServer()
    {
        try
        {
            serverListener = new TcpListener(System.Net.IPAddress.Parse(host), port);
            serverListener.Start();
            Debug.Log($"[AGIseed Bridge] En attente de connexion AGIseed sur {host}:{port}...");
            isRunning = true;

            while (isRunning)
            {
                client = serverListener.AcceptTcpClient();
                stream = client.GetStream();
                Debug.Log("[AGIseed Bridge] Agent Python AGIseed connecté avec succès !");

                byte[] buffer = new byte[4096];
                while (isRunning && client.Connected)
                {
                    int bytesRead = stream.Read(buffer, 0, buffer.Length);
                    if (bytesRead == 0) break;

                    string jsonMsg = Encoding.UTF8.GetString(buffer, 0, bytesRead).Trim();
                    HandleIncomingMessage(jsonMsg);
                }
            }
        }
        catch (Exception ex)
        {
            Debug.LogWarning($"[AGIseed Bridge] Exception réseau : {ex.Message}");
        }
    }

    void HandleIncomingMessage(string json)
    {
        try
        {
            // Parsing simple du message JSON de commande (RESET ou STEP)
            if (json.Contains("RESET"))
            {
                // Réinitialiser la position
                SendObservations();
            }
            else if (json.Contains("STEP"))
            {
                // Extraire les actions du JSON et envoyer les nouvelles observations
                SendObservations();
            }
        }
        catch (Exception ex)
        {
            Debug.LogError($"[AGIseed Bridge] Erreur de parsing message : {ex.Message}");
        }
    }

    void SendObservations()
    {
        if (stream == null || !stream.CanWrite) return;

        // Formater les observations sous format JSON : {"observation": [...]}
        StringBuilder sb = new StringBuilder();
        sb.Append("{\"observation\": [");
        for (int i = 0; i < observations.Length; i++)
        {
            sb.Append(observations[i].ToString("F4", System.Globalization.CultureInfo.InvariantCulture));
            if (i < observations.Length - 1) sb.Append(", ");
        }
        sb.Append("]}\n");

        byte[] data = Encoding.UTF8.GetBytes(sb.ToString());
        stream.Write(data, 0, data.Length);
        stream.Flush();
    }

    void FixedUpdate()
    {
        // 1. Appliquer les actions motrices calculées par l'agent
        if (rb != null)
        {
            Vector3 moveForce = new Vector3(currentActions[0], currentActions[1], currentActions[2]) * moveSpeedMultiplier;
            rb.AddForce(moveForce);
        }

        // 2. Mettre à jour les observations (LiDAR 3D, Position, Vitesse)
        UpdateSensors();
    }

    void UpdateSensors()
    {
        // 16 Raycasts LiDAR 3D circulaires autour de l'agent
        for (int i = 0; i < lidarRayCount; i++)
        {
            float angle = i * (360f / lidarRayCount);
            Vector3 dir = Quaternion.Euler(0, angle, 0) * transform.forward;
            RaycastHit hit;
            if (Physics.Raycast(transform.position, dir, out hit, lidarMaxDistance))
            {
                observations[i] = hit.distance / lidarMaxDistance;
            }
            else
            {
                observations[i] = 1.0f;
            }
        }

        // Position normalisée
        observations[16] = transform.position.x / 50f;
        observations[17] = transform.position.y / 50f;
        observations[18] = transform.position.z / 50f;

        // Vitesse normalisée
        if (rb != null)
        {
            observations[19] = rb.linearVelocity.x / 10f;
            observations[20] = rb.linearVelocity.y / 10f;
            observations[21] = rb.linearVelocity.z / 10f;
        }
    }

    void OnDestroy()
    {
        isRunning = false;
        if (stream != null) stream.Close();
        if (client != null) client.Close();
        if (serverListener != null) serverListener.Stop();
        if (networkThread != null && networkThread.IsAlive) networkThread.Abort();
    }
}
