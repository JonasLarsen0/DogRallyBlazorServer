namespace DogRallyBlazorServer.Models.Responses;

public class GetAllTracksResponse: BaseResponse
{
    public List<Track> Tracks { get; set; }
}
