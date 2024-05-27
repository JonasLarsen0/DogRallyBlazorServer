namespace DogRallyBlazorServer.Models.Responses;

public class GetAllTracksResponse: BaseResponse //Getting the list of tracks. Used in TrackService.cs
{
    public List<Track> Tracks { get; set; }
}
