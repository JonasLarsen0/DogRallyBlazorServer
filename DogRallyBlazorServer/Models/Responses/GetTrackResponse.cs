namespace DogRallyBlazorServer.Models.Responses
{
    //Setting the properties for the track. Used in TrackService.cs
    public class GetTrackResponse: BaseResponse
    {
        public Track Track { get; set; }
    }
}
